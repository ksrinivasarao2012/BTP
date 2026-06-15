# Pending Work (Phase B polish) + Adversary Design for Phase C/D

**Date:** 2026-06-15
**Purpose:** (A) record the Phase B paper-polish tasks so they aren't forgotten, and
(B) decide — grounded in the literature review — how many traitors and which adversary
types to use in Phase C/D.

---

# PART A — Pending Phase B tasks (do NOT block Phase C; for the writeup)

These can run in parallel with Phase C development. Totals & success are already valid;
these refine the *details* and add comparisons.

### A1. Re-run collision SPLITS with the fixed attribution (fast, inference only)
The drone-vs-obstacle split for these was logged before the `collision_type` fix
(their **totals and success are valid** — only the split is stale/missing):
```powershell
python eval_comm.py 3          # comm=3 split
python eval_comm.py 5          # comm=5 split
python eval_comm.py inf        # V14 unlimited split
python eval_comm_blackout.py   # blackout split (also now logs drone-coll)
```
Output → `results/comm_sweep/`. After this, every condition has a correct drone-vs-obstacle breakdown.
**Why it matters:** consistency for the ablation table; confirms the comm story ("removing comm raises *drone* collisions").

### A2. External baseline — ORCA (for "is our method actually good?")
- Script exists: `Phase B/Phase_B5_Synchronization/v10_IEEE_Final/evaluate_orca.py`
- Run ORCA on the **same densities (0.20, 0.30)** and report success/collision next to the 8m model.
- Optional second baseline: vanilla MAPPO (no Dijkstra/wall-glide) and/or a potential-field planner.
- Literature comparison points exist: papers [95]/[97] benchmark against **MAPPO, MADDPG, Q-learning** — cite/compare.

### A3. Statistical significance — multi-seed (venue-dependent, heavier)
- Retrain the **headline model (`comm8_lidar`)** with ≥3 seeds; report **mean ± std**.
- Only needed if the target venue demands significance (top-tier). For a thesis/applied venue, note as a limitation.

### A4. Lock the reported Phase B model
- **`comm8_lidar`** = 95.55% / 91.10% (0.20/0.30), CTDE-clean (LiDAR congestion, leakage-tested).
- This is the model the paper reports AND the Phase C transfer base.

---

# PART B — How many traitors? (grounded in the literature review)

The literature gives concrete bounds for `n = 10` drones, `f` = number of traitors:

| Source (from the review) | Bound / result | Implication for n=10 |
|--------------------------|----------------|----------------------|
| Classic Byzantine fault tolerance | **f < n/3** | tolerable up to **f = 3** (≤ 3.33) |
| "Following Leaders in Byzantine Multirobot Systems" [row 110-114] | **n − 2f** robots can still reach | f=1→8, f=2→6, f=3→4 reach (worst case) |
| "Resilient MARL w/ Function Approximation" [row 38-44] | needs a **(2H+1)-robust network** for H Byzantine | connectivity must scale with f |

### Decision: sweep **f ∈ {1, 2, 3}** (= 10%, 20%, 30%), headline at **f = 2 (20%)**

- **f = 1 (10%):** mild — does the defense help even with one traitor?
- **f = 2 (20%):** **headline** — clean fraction, within the classic f<n/3 tolerable regime.
- **f = 3 (30%):** stress — at the edge of the Byzantine bound (f<n/3).
- **(optional) f = 4 (40%):** **breakdown point** — *beyond* classic guarantees; expect even a good defense to degrade. Showing where it breaks is a strong, honest result.

### Metric reminder (decided earlier)
```
honest_success = (honest drones that reached) / (n - f)      # exclude traitors
```
Also report: traitor-caused collisions, detection rate, false-positive rate, time-to-detect.

---

# PART C — "Different adversarial agents" (your idea — strongly supported)

The review shows the field tests **multiple adversary models**, not just one. Build a
**taxonomy** and sweep adversary TYPE × COUNT. Each maps to a paper:

| # | Adversary type | What it does | Phase | Lit. anchor |
|---|----------------|--------------|-------|-------------|
| **T1** | **Deceptive (comm-lie)** | broadcasts FALSE position / velocity / stagnation; physically behaves normally | **C** | "H₂ Resilient Consensus under **Deception Attack**" [20-27] |
| **T2** | **Byzantine (arbitrary)** | random/erratic malicious actions + inconsistent broadcasts | C/D | "Resilient MARL w/ Function Approx." [38-45]; "Byzantine Multirobot (Blockchain)" [110-116] |
| **T3** | **Jamming (comm-denial)** | drops / noises / floods the communication channel (no useful broadcast) | C | UAV anti-jamming game [69]; FDQN anti-jamming [86]; swarm relay anti-jamming [95] |
| **T4** | **Faulty (non-malicious)** | sensor/actuator failure → behavioral outlier (not hostile intent) | C | "Fault Detection via Behavioral Outlier" [101-108] |
| **T5** | **Aggressive / physical** | ramming honest drones, blocking chokepoints | **D** | (physical threat; combine with T1 for hardest case) |

**Note T3 vs your Phase B result:** jamming ≈ the *blackout* you already studied (comm removed). You showed blackout is survivable via LiDAR fallback — so **jamming is the *weak* attack; deception (T1) is the *dangerous* one** (drones act on lies). This is a finding you can state directly.

### Recommended Phase C adversary progression
1. **T1 deception** (primary) — false velocity is the most damaging (poisons anticipation).
2. **T4 faulty** — easier case; shows the detector generalizes beyond malice.
3. **T2 Byzantine** — hardest deception variant (inconsistent, unpredictable).
4. (Phase D) **T5 + T1** — physical ramming while lying = the worst case.

---

# PART D — The Phase C/D experiment matrix

Sweep three axes; the headline is **defense ON vs OFF**:

```
adversary TYPE  ∈ {T1 deception, T4 faulty, T2 byzantine, (D) T5+T1}
traitor COUNT   ∈ {1, 2, 3, (4 breakdown)}
density         ∈ {0.20, 0.30}
defense         ∈ {trust OFF, trust ON}      <-- the comparison
```

**Headline figures:**
- `honest_success` vs traitor count, trust ON vs OFF (one line per defense) — per adversary type.
- detection-rate / false-positive-rate vs traitor count (shows the mechanism works, not just the score).

Don't run the full cross product first — start with **T1, f=2, density 0.30, trust ON vs OFF** (the single most informative cell), then expand.

---

# PART E — Literature support for OUR trust mechanism (use these as citations)

Our design (persistent identity-indexed trust table = immune memory, updated from
comm-vs-LiDAR discrepancy, retain-when-unverifiable, fast-rise/slow-decay) is well-grounded:

| Our design choice | Supported by |
|-------------------|--------------|
| Immune-inspired trust / "T-Cell", negative selection of non-self | "Artificial Immune System (negative selection)" [78-80] |
| Observe neighbor **behavior over a sliding window** → feature vector → detect outliers | "Fault Detection via Behavioral Outlier Detection" [101-108] (decentralized, immune-inspired) |
| Multi-factor / persistent trust aggregation (direct + indirect + capability) | "RTE: Rapid & Reliable Trust Evaluation (IoV)" [56-63] |
| Learning-based resilience instead of fixed controllers; bounded trust under Byzantine | "Resilient MARL w/ Function Approx." [38-45]; H₂ deception consensus [20-27] |
| Robustness without explicit adversary training (regularization complement) | "MIR³ robust MARL" [47-54] |
| Byzantine reachability guarantee (n−2f) to frame expectations | "Byzantine Multirobot (Blockchain)" [110-116] |

**Positioning statement for the paper:** prior resilient-MARL work is mostly *model-based*
(H₂, W-MSR trimming, blockchain) or *robustness-by-regularization* (MIR³), and immune-inspired
detection is mostly for *non-malicious faults* (behavioral outliers). **Our contribution = a
learning-based, immune-inspired (T-Cell) trust mechanism that detects *deceptive* agents by
cross-checking communication against LiDAR, integrated end-to-end in MARL navigation.** That
combination is the gap the review repeatedly points to (rows [27], [36], [45], [108], [116]
all say "extend to learning-based / UAV-swarm / deceptive agents").

---

# PART F — Consolidated next-step checklist

### Phase B polish (parallel, optional)
- [ ] A1: re-run comm3 / comm5 / inf / blackout for correct collision splits
- [ ] A2: ORCA baseline at 0.20 & 0.30 (+ optional vanilla-MAPPO)
- [ ] A3: 3-seed the `comm8_lidar` headline (if venue needs significance)
- [ ] A4: lock `comm8_lidar` as the reported Phase B model

### Phase C kickoff (the real next phase)
- [ ] Decide trust = hand-designed detector first (recommended) vs learned head
- [ ] Env: add traitors (`num_traitors` f∈{1,2,3}), T1 deception (corrupt received broadcasts)
- [ ] Trust: persistent identity-indexed table + update/retain/decay → sync 4th slot
- [ ] Metrics: honest_success (over n−f), detection / false-positive rate
- [ ] Train: transfer from `comm8_lidar`; curriculum 0→1→2 traitors, mild→strong deception
- [ ] First cell: T1, f=2, density 0.30, trust ON vs OFF
- [ ] Expand: adversary types (T4, T2), counts (1/3/4), densities

---

# NOTES / QUESTIONS FOR CLAUDE
-
-
