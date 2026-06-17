# Phase C/D — Plan of Action (from 2026-06-16)

This plan picks up from `PHASE_CD_PROGRESS_LOG.md`. The three reactive-motion defense classes
(evasion, coordination, speed asymmetry) are **all ruled out** by perfect-info oracles. The
project now stands at a single, well-defined fork decided by one pending experiment.

**Governing discipline (do not break):** oracle/probe BEFORE training; no fabricated numbers;
verify code before asserting (watch stale `__pycache__`); honest_success excludes traitors;
upper-bound oracles bound *feasibility*, not deployability.

---

## THE FORK — decided by the beyond-sensing comm probe (`probe_comm_range.py`)

```
                       probe_comm_range.py (running)
                                 │
            honest_success RISES with comm range?
                 │                                  │
                YES                                 NO / FLAT
   (comm has non-redundant,              (local sensing dominates,
    poisonable beyond-sensing info)        comm is redundant)
                 │                                  │
        ►  PATH P: POSITIVE                 ►  PATH L: FUNDAMENTAL-LIMIT
           Trust-Aware defense paper           paper (negative, theory-backed)
```

A POSITIVE result is decisive (helps despite M0 not being trained for it). A NULL is strongly
suggestive but, because of the training confound, must be confirmed by a short retrain at
extended comm before declaring the limit final (see Path L, step L0).

---

## Immediate next steps (regardless of fork)

1. **[RUNNING] Read the comm-range probe result** (`results/phase_c_probe/comm_range_f2.csv`,
   30 maps). Apply the decision rule above.
2. **Lock the confirmed oracle table** into the paper draft (numbers in the progress log §3).
   Already at 200 maps for coordination and speed; evasion and no-defense already at 200.
3. **Optionally widen the attack characterization** (helps both paths, cheap):
   - f = 1 and f = 3 rammers at 200 maps (`probe_ram.py`) to show the per-rammer ~−9 pp scaling.
   - A cooperative/pincer rammer variant (two rammers coordinating on one victim) — strengthens
     the threat model. Build by editing `_ram_action` to a shared target; oracle-test first.

---

## PATH P — Positive "Trust-Aware" defense paper  (only if comm probe is POSITIVE)

**Thesis:** when communication carries non-redundant, beyond-sensing information, a Byzantine
traitor can poison it; a T-Cell trust mechanism that identifies and discounts the liar restores
success. This earns the project's "Trust-Aware" title.

### P0 — Confirm the honest channel helps (gate)
- Re-run `probe_comm_range.py` at 200 maps. Confirm the rise is real and sized.
- If the rise needs retraining to appear, train a short variant at the winning comm range and
  re-measure (this becomes the honest baseline the attack degrades).

### P1 — Design the channel attack (the thing trust defends)
- **Byzantine / false threat-report traitor:** broadcasts fabricated beyond-sensing info
  (e.g. "rammer here" / false neighbor position) on the extended channel — content the victim
  **cannot** verify with LiDAR (out of sensing range). This is the deception that is NOT inert.
- Env already has `deception_mode ∈ {none, false_velocity, false_position}` and
  `_falsify_broadcast(...)`. Add a `false_alert` mode if threat-reports are a separate field.
- **Oracle-test the attack first:** measure honest_success drop with the liar and NO defense.
  If the drop is small, the attack is weak → reconsider before building trust.

### P2 — Build the T-Cell trust mechanism (the defense)
- Per-neighbor trust score updated from agreement between a neighbor's broadcast and what the
  drone *can* verify (LiDAR when in range; consistency over time when out of range). Discount /
  gate low-trust broadcasts. Spec: `PHASE_C_TRUST_DESIGN.md`.
- **Oracle-test the defense first:** a perfect-trust oracle (knows the traitor IDs, ignores
  their broadcasts) — upper bound. If even perfect trust doesn't recover success, do not train.

### P3 — Train the learned defense (M2)
- Transfer from M0; curriculum with the Byzantine traitor (and a false-alert traitor so trust
  must distinguish real vs. fake alerts). Headline: **M1 (no defense) vs M2 (trust defense)**
  at f = 1, 2, 3, with the false-alert traitor present so the title is earned.
- Report: honest_success recovery, trust-score ROC (traitor identification), and the cost when
  there is no traitor (trust must not hurt the honest case).

### P4 — Paper
- Contribution = a working trust-aware defense against channel poisoning, validated oracle→trained.
- Threat-model scoping: physical ramming (limit) vs. channel poisoning (defendable) — the two
  regimes are the paper's spine.

---

## PATH L — Fundamental-limit paper  (if comm probe is NULL)

**Thesis:** a decentralized swarm with equal-speed dynamics cannot defend a target against a
physical (ramming) adversary in obstacle-dense space — by evasion, coordination, OR speed
asymmetry. Comm deception is inert because local sensing dominates the channel. Grounded in
pursuit-evasion theory, with the **obstacle caveat** as the novel finding.

### L0 — Close the comm confound (required before declaring the limit final)
- Short retrain of M0 at extended comm range (e.g. 16–20 m); re-measure vs rammers.
- If still flat → the limit is robust (comm genuinely redundant). If it now helps → the result
  was a training artifact and we switch to PATH P. **This gate prevents a false negative.**

### L1 — Assemble the evidence
- The oracle table (progress log §3): all three defenses capped at ~72–80% (perfect-info → holds
  for *any* learned reactive-motion policy, the key to it being a real *limit*, not "M1 didn't learn").
- Deception-inert result (LiDAR > comm range) to scope the threat model.
- Attack scaling: per-rammer ~−9 pp; f = 1/2/3 table.
- Mechanism plots: obstacle-collision rising with boost (speed-asymmetry failure); drone-collision
  shifting under coordination (blocker-trades-victim failure).

### L2 — Theory section (the spine)
- Pure-pursuit, equal speed → interception is geometrically guaranteed → evasion can't escape
  (matches the ~80% oracle ceiling).
- Faster evader → escape guaranteed **in open space**; our obstacle result shows the obstacle
  field collapses that advantage (faster evader trades drone- for obstacle-collisions). State and
  support the obstacle caveat — this is the contribution beyond textbook pursuit-evasion.

### L3 — Paper
- A principled negative result: only **role/speed asymmetry in open space** breaks the symmetry;
  in obstacle-dense decentralized swarms, reactive defense against an equal-speed rammer is
  fundamentally bounded.

---

## Honest caveats (keep us disciplined)
- No path is a guarantee of publication; PATH P is the higher-ceiling outcome but its prior is
  genuinely uncertain and rides entirely on the comm probe.
- Oracles are upper bounds (true positions) — they bound feasibility, not deployability.
- Speed/comm changes alter the system → must be justified and their cost reported; don't hide them.
- Do NOT train any defense before its oracle clears the bar. If both the comm probe and its
  retrain confirm null, write PATH L and stop building.

---

## Decision checklist
- [ ] comm-range probe read (30 maps) → fork chosen
- [ ] (if positive) comm-range 200-map confirm + P1 attack oracle
- [ ] (if null) extended-comm retrain confirm (L0)
- [ ] f=1/3 rammer scaling table (both paths)
- [ ] paper draft started for the chosen path
