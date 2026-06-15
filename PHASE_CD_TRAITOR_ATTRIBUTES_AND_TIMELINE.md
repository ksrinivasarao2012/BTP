# Phase C & D — Traitor Attributes + Time Estimates

**Date:** 2026-06-15
**Purpose:** define exactly what a traitor *is* (its attributes/behaviours) in Phase C vs Phase D,
and give honest time estimates per step, grounded in your actual Phase B timings.

**Timing baseline (measured this project):**
- one `train_comm.py` run = ~50 min (5M steps, transfer, 10 workers)
- one density-sweep eval (2 densities × 200 maps) = ~30–60 min (single-process CPU)

---

# PART 1 — What is a traitor? (attributes)

A traitor is the same drone body (LiDAR-visible, same dynamics) but with two attribute groups:
**(A) what it BROADCASTS** (the comm channel — corruptible) and **(B) how it MOVES** (its physics).

| Attribute | Honest drone | Phase C traitor | Phase D traitor |
|-----------|--------------|-----------------|-----------------|
| Goal | reach shared goal | not trying to reach (or pretends) | actively disrupt honest drones |
| **Broadcast position** | true | **falsified** (offset/random) | falsified |
| **Broadcast velocity** | true | **falsified** (e.g. opposite of motion) | falsified |
| **Broadcast stagnation** | true | **falsified** ("I'm stuck") | falsified |
| **Physical motion** | navigate to goal | **plausible/benign** (just lies) | **hostile** (ram / block) |
| LiDAR signature | true (visible) | true (visible) | true (visible) |
| Counts toward success? | yes (n−f denom) | **no** (excluded) | no |

**Key split:** Phase C = the traitor **LIES but moves benignly**. Phase D = the traitor **LIES *and*
physically attacks**. LiDAR always sees the traitor's real body; only the *broadcast* is corruptible.

---

# PART 2 — PHASE C traitor attributes (DECEPTION)

The traitor navigates plausibly but **corrupts the broadcast** honest drones receive. Variants:

| ID | Attribute (what's falsified) | Effect on honest swarm | Difficulty |
|----|------------------------------|------------------------|-----------|
| **C-T1a** | **false position** — broadcast pos offset from true | honest plan around a phantom; collide with real body | easy to detect (pos vs LiDAR) |
| **C-T1b** | **false velocity** — broadcast vel opposite/random | poisons collision *anticipation* → honest dodge wrong way | harder, most damaging |
| **C-T1c** | **false stagnation** — broadcast "stuck" | honest reroute/wait needlessly → timeouts | subtle |
| **C-T1d** | **combined** (a+b+c) | maximal corruption of the comm channel | hardest |
| **C-T2** | **Byzantine** — randomly inconsistent broadcasts every step | unpredictable; tests detector robustness | hard |
| **C-T4** | **faulty (non-malicious)** — broadcast frozen/noisy due to "sensor fault" | behavioural outlier, no intent | baseline/easy |

**Phase C physical behaviour:** benign — the traitor still moves like a normal navigator (or wanders).
It does **not** ram. (That's Phase D.) So Phase C isolates "can the swarm detect & ignore LIES."

**What defends it:** the trust mechanism (cross-check broadcast vs LiDAR) → distrust → ignore the lie,
fall back on LiDAR. (Spec in `PHASE_C_TRUST_DESIGN.md`.)

---

# PART 3 — PHASE D traitor attributes (DECEPTION + AGGRESSION)

The traitor adds **hostile physical behaviour** on top of (optional) lying:

| ID | Attribute (physical) | Effect | Difficulty |
|----|----------------------|--------|-----------|
| **D-T5a** | **ramming** — steer toward nearest honest drone to collide | forces collisions; LiDAR sees it but it's actively hostile | hard |
| **D-T5b** | **blocking** — park on chokepoints / shortest path | causes timeouts / detours | medium |
| **D-T5c** | **ram + lie** (D-T5a + C-T1b) | charges while broadcasting false velocity → anticipation poisoned *and* physical threat | **hardest (headline D)** |

**Phase D physical behaviour:** hostile. LiDAR detects the physical threat, but avoiding an *actively
adversarial* mover (that also lies) is genuinely hard.

**What defends it:** full TA-MAPPO = trust mechanism (ignore lies) + learned robust evasion (treat
low-trust physical neighbours as high-priority dynamic obstacles).

---

# PART 4 — Time estimates

## 4.1 Phase C

| Step | Work | Est. time |
|------|------|-----------|
| C-1 | **Env fork**: traitor spawn + deception (corrupt broadcasts), metrics (honest_success, detection) | **2–4 days** (dev + debug) |
| C-2 | **Trust mechanism**: persistent table + update/retain/decay + sync-slot wiring (hand-designed) | **2–4 days** (dev + debug) |
| C-3 | **Train M1** (trust OFF, traitors) — transfer from comm8_lidar | ~50 min/run × (curriculum 0→1→2 traitors ≈ 2–3 stages) → **~2–3 hrs** |
| C-4 | **Train M2** (trust ON, traitors) | **~2–3 hrs** |
| C-5 | **Eval** M0 zero-shot + M1 + M2, at f∈{1,2,3} × 2 densities | ~30–60 min per (model × f) ≈ 3 models × 3 f ≈ **6–9 hrs** compute (unattended) |
| C-6 | **Tune** trust params (tau, alpha_rise/decay) — a few train+eval iterations | **2–5 days** (the real time sink) |
| C-7 | **Adversary-type sweep** (T1 variants, T2, T4) | each type = 1 train + eval ≈ ~1.5 hr compute; ~**1–2 days** wall-clock |

**Phase C total (realistic): ~2–3 weeks** of focused work.
- Compute is small (~15–25 hrs, unattended).
- The time is **development + tuning**, not GPU.
- Fastest path to first result (T1b, f=2, M1 vs M2): **~1 week** if env+trust go smoothly.

## 4.2 Phase D

| Step | Work | Est. time |
|------|------|-----------|
| D-1 | **Env**: add hostile traitor policies (ramming, blocking) on top of Phase C | **2–4 days** |
| D-2 | **Train** D-models (TA-MAPPO on vs off), transfer from Phase C M2, aggression curriculum (passive→block→ram→ram+lie) | ~50 min/run × ~4 curriculum stages × 2 models → **~6–8 hrs** compute |
| D-3 | **Eval** D-models at f∈{1,2,3} × attack types (ram/block/ram+lie) × 2 densities | **~8–12 hrs** compute (unattended) |
| D-4 | **Tune** robustness/evasion + trust under aggression | **3–7 days** |

**Phase D total (realistic): ~2–3 weeks.**

## 4.3 Grand total

| Phase | Realistic wall-clock |
|-------|----------------------|
| Phase C | ~2–3 weeks |
| Phase D | ~2–3 weeks |
| **C + D together** | **~5–6 weeks** of focused work |

**Honest notes on the estimate:**
- The bottleneck is **development + parameter tuning**, not GPU time (compute is modest and unattended).
- Estimates assume the env fork and trust mechanism work without major surprises; budget +1 week buffer.
- The single most informative first milestone (worth doing before the full sweep): **C-T1b, f=2,
  density 0.30, M1 vs M2** → if M2 clearly beats M1, the core thesis is proven and the rest is breadth.

---

# PART 5 — Recommended order (fastest to a defensible result)

1. **Env fork + C-T1b** (false velocity — most damaging) + **honest_success metric**. (C-1)
2. **Trust table (hand-designed)** wired to sync slot. (C-2)
3. **Train M1 & M2** at f=2; **eval at density 0.30**. (C-3/4/5 minimal)
4. **If M2 > M1 → core thesis proven.** Then expand: f∈{1,3}, other attack types, density 0.20.
5. **Tune** trust params for the strongest gap. (C-6)
6. **Phase D** only after Phase C result is solid.

---

# NOTES / QUESTIONS FOR CLAUDE
-
-
