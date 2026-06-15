# Phase C — Adaptive Trust (T-Cell) Design & Justification  [CONSOLIDATED v2]

> **Updated:** 2026-06-15. Supersedes the 2026-06-14 draft.
> **Changes from v1 (important):**
> - Trust lives in the **sync 4th slot** backed by a **persistent identity-indexed table** —
>   NOT in `is_active` (is_active is a presence mask; a traitor has is_active=1 but is untrusted).
> - Trust scale is **0 = trusted → 1 = traitor** (suspicion), consistent with the Phase B all-zeros.
> - Base env is **`swarm_env_step_B10_8_0m.py`** (parameterized comm range, LiDAR congestion).
> - Adds the **comm ≤ LiDAR verifiability** justification and the **M0/M1/M2 model strategy**.
> **Status:** DESIGN SPEC — not yet implemented. This is the build blueprint.

---

## 0. Honest scope — what exists now vs. the Phase C addition

| Component | In the model today? | Notes |
|---|---|---|
| Flocking bio-inspiration (cohesion/separation/alignment) | ✅ | reward terms incl. velocity `cos_sim` alignment |
| Danger signals (TTC, proximity penalties) | ✅ | collision shaping — substrate for the immune layer |
| CTDE structure (actor local 130 / critic global 520) | ✅ | leakage-tested PASS |
| Reserved trust slot (sync 4th value, constant 0.0) | ✅ | the dimensional home for trust |
| Persistent trust table / T-Cell / traitor detection | ❌ | **the Phase C contribution** |

> Paper sentence: *"The architecture provides the substrate — flocking coordination, per-step danger
> signals, a CTDE policy, and a reserved neighbour-trust slot. The adaptive trust (immune / T-cell)
> layer is introduced in Phase C, adding a second layer of bio-inspiration atop the first (flocking)."*

---

## 1. Justification of the 8.0m communication range (4 prongs)

| # | Justification | Evidence |
|---|---------------|----------|
| 1 | **Empirical — flat region** | comm sweep 3/5/8/∞ all within ≤1pp success → 8m not cherry-picked |
| 2 | **Active, not vacuous** | binding diagnostic: gate binds ~10% of steps @0.30 (≈28% of field diagonal) |
| 3 | **Design — safety from sensing** | comm (8m) < LiDAR (12m) ⇒ collision-critical info always available on-board; comm is a coordination *bonus*, not a safety *requirement* |
| 4 | **★ Phase C necessity — verifiable trust ★** | trust = cross-check "what j SAYS (comm)" vs "what we SEE (LiDAR)". Only possible when **comm ≤ LiDAR**, so every neighbor we can hear we can also verify. comm > LiDAR ⇒ unverifiable claims ⇒ undetectable lies. |

> Paper sentence: *"We set comm (8m) within LiDAR (12m). Empirically it lies on the flat region of the
> performance-vs-range curve; functionally, comm ≤ LiDAR guarantees that any neighbor we can communicate
> with is also one we can sense — a prerequisite for verifying communicated state against observed
> behaviour in the trust mechanism."*

(Do NOT justify comm<LiDAR as "radio is weaker than LiDAR" — false. It is a deliberate design choice.)

---

## 2. Phase C model strategy — "trust OFF" is NOT the Phase B model

| Model | Trained w/ traitors? | Trust mechanism? | Role |
|-------|:---:|:---:|------|
| **M0 — `comm8_lidar`** (Phase B) | No | No | transfer base + "naive swarm" vulnerability reference |
| **M1 — Trust OFF** | **Yes** | **No** (trust slot = 0) | **fair baseline** (robustness without trust) |
| **M2 — Trust ON** | **Yes** | **Yes** | **proposed method (TA-MAPPO)** |

- **Headline comparison = M1 vs M2** (both retrained with traitors; only difference = trust mechanism → isolates its contribution).
- **M0 vs traitors (zero-shot)** = motivating "look how bad it gets" reference — NOT the main baseline.
- Comparing M0 vs M2 would conflate "retrained on traitors" + "has trust" → unfair. Use **M1 vs M2**.
- Both M1 and M2 **transfer from M0 (`comm8_lidar`)**, same curriculum/seeds/densities.
- (Optional sanity) take M2 and **zero its trust slot at eval** — eval-time ablation showing how much M2 relies on trust. M1 is still the rigorous baseline.

---

## 3. The trust mechanism — full spec

**Principle (immune analogy / Danger Theory):** each honest drone keeps a **persistent memory** of
which neighbors behaved like "non-self" (their broadcasts contradict what we sense / steer us toward
danger), built by comparing **what they say** (comm) to **what they do** (LiDAR), and **remembers** it
even when the neighbor is out of range.

### 3.1 State (per honest agent `i`)
```
trust[i][j]  ∈ [0,1]  for all j != i     # 0 = trusted, 1 = certain traitor; PERSISTENT this episode
sensed_pos_hist[i][j]                      # ring buffer of LiDAR-sensed positions of j (for velocity est.)
```
- **Identity-indexed & persistent** → survives j leaving/re-entering the closest-5 (no reputation laundering).
- **Init:** `trust[i][j] = 0` (everyone trusted — consistent with Phase B's all-zero sync pad).

### 3.2 Per-step update (agent `i`, neighbor `j`)

**Step 1 — verifiability:**
```
d   = ||pos_i - pos_j||
hear = (j broadcasts) AND (d <= comm_range)     # we received j's message
see  = (d <= lidar_range)                        # LiDAR senses j's true position
verifiable = hear AND see                        # need both to cross-check (guaranteed since comm<=lidar)
```

**Step 2 — if verifiable, discrepancy (what j SAYS vs what we SEE):**
```
pos_disc = ||claimed_pos_j - sensed_pos_j|| / D_p          # claimed = broadcast, sensed = LiDAR
est_vel  = (sensed_pos_j(t) - sensed_pos_j(t-1)) / dt      # velocity we infer from our own sensing
vel_disc = ||claimed_vel_j - est_vel|| / D_v
discrepancy = clip(w_p*pos_disc + w_v*vel_disc, 0, 1)
```

**Step 3 — update (fast-rise / slow-decay):**
```
if discrepancy > tau:                              # caught a mismatch
    trust[i][j] += alpha_rise  * (1 - trust[i][j]) # jump toward 1 (fast)
else:                                              # consistent behaviour
    trust[i][j] -= alpha_decay * trust[i][j]       # ease toward 0 (slow)
```
`alpha_rise >> alpha_decay` → suspicion accrues fast, forgiveness is slow (adversary-resistant).

**Step 4 — if NOT verifiable (out of range):**
```
RETAIN trust[i][j]      # immune memory; a flagged traitor stays flagged
# optional very-slow forgetting: trust[i][j] -= alpha_idle * trust[i][j],  alpha_idle ~ 0
```

### 3.3 Exposure to the policy — sync 4th slot (no dim change)
- For the **closest-5** neighbors, write `trust[i][j]` (looked up **by identity** from the table) into
  the **4th value of each sync entry** (the Phase B `0.0` pad).
- The persistent table means a returning traitor gets its **remembered** suspicion, not a fresh 0.
- **Keep `is_active` as the presence mask** (separate concept). Why not use `is_active` for trust:
  a traitor is present (`is_active=1`) but untrusted → presence ≠ trust; conflating them loses the
  distinction. Keep them separate.
- Why closest-5 is enough: you only *act on* nearby drones; the **table still remembers all 10**, and a
  distant traitor's suspicion is restored the moment it enters the closest-5.

### 3.4 How the policy uses it (LEARNED in Phase C, not hand-coded)
With traitors present during training, the policy (M2) learns to:
- **discount** a high-suspicion neighbor's *communicated* pos/vel (fall back on its **LiDAR** position), and
- give high-suspicion neighbors **extra clearance**.

We provide the trust *signal*; RL learns the *response*. (Physical safety is always backstopped by LiDAR,
which sees the traitor regardless of trust.)

### 3.5 Parameters (tune + report sensitivity)
| Param | Meaning | Start |
|-------|---------|-------|
| comm_range / lidar_range | ranges (comm ≤ lidar required) | 8.0 / 12.0 |
| tau | discrepancy threshold to flag | 0.2–0.3 |
| alpha_rise / alpha_decay | rise vs forgive rates | 0.3 / 0.02 |
| w_p / w_v | position vs velocity weight | 0.5 / 0.5 |
| D_p / D_v | discrepancy normalizers | 1.0 m / max_velocity |

### 3.6 Implementation variant
- **(A) Hand-designed detector (do FIRST):** the equations above, fixed params. Interpretable — you can
  plot `trust[i][traitor](t)` and watch it spike. Policy learns to use it.
- **(B) Learned trust head (later):** small NN → trust score, end-to-end.

---

## 4. Immune / Danger-Theory mapping (the biology doing real work)

Lead with **Danger Theory** (Matzinger): respond to **danger/damage signals**, not mere difference —
strong anchor because the env already computes danger signals (TTC, proximity).

| Immunology | Our mechanism |
|---|---|
| Self / non-self (T-cell negative selection) | honest = self; traitor (broadcast ≠ sensed) = non-self |
| Antigen / signature | neighbor's broadcast vs own LiDAR — mismatch = foreign signature |
| **Danger signal (Danger Theory)** | a broadcast that contradicts LiDAR / would steer us into danger |
| Adaptive / clonal response | `trust` rises on repeated danger, eases on agreement (§3.2) |
| **Immune memory** | persistent `trust[i][j]` table, retained when out of range (§3.1, Step 4) |
| Tolerance / anti-autoimmunity | threshold `tau` + slow decay → avoid falsely distrusting honest drones |

Claim **functional analogy** ("inspired by"), not biophysical fidelity. Novelty = the **integration**:
CTDE + limited-range comm + Danger-Theory-inspired persistent adaptive trust for resilient swarm
navigation under deceptive traitors.

---

## 5. Goal channel vs neighbour channel (clean separation)

- **Goal channel** (`to_goal`, `dist_goal`): from a **Dijkstra planner on the static map** — **NOT
  spoofable** by traitors (map-derived; traitors are drones, not map obstacles). Frame as **hierarchical
  navigation** (classical global planner + learned local controller); don't claim "mapless."
- **Neighbour channel** (obs_neighbors + sync): **spoofable → the only channel the trust mechanism
  defends.** Goal-seeking stays reliable under attack; trust guards coordination.

---

## 6. Adversary numbers & types (grounded in the literature review)

- **Counts:** classic Byzantine bound `f < n/3` → for n=10, sweep **f ∈ {1,2,3}** (10/20/30%),
  headline **f=2**, optional **f=4** as breakdown. ("Byzantine Multirobot" gives n−2f reachability.)
- **Types (sweep these):** T1 deception (false pos/vel/stagnation) [primary], T4 faulty (non-malicious),
  T2 Byzantine (arbitrary), T3 jamming (≈ blackout — already shown survivable), T5 physical ramming
  (Phase D). See `PENDING_WORK_AND_ADVERSARY_DESIGN.md` for the full taxonomy + citations.
- **Metric:** `honest_success = reached / (n − f)` (exclude traitors). Plus detection / false-positive /
  time-to-detect. **No specific success number in the paper until Phase C runs produce it.**

---

## 7. Implementation checklist (Phase C)

### Env (`swarm_env_step_B10_8_0m.py` → Phase C fork)
- [ ] `num_traitors` (f) / `num_honest` (n−f) honored; spawn f traitors.
- [ ] Traitor deception: corrupt the broadcast honest agents receive (false pos/vel/stagnation); keep traitor's true LiDAR signature.
- [ ] `sensed_pos_hist[i][j]` ring buffer for velocity estimation.
- [ ] `trust[i][j]` table, persistent, init 0; update/retain/decay per §3.2.
- [ ] Write trust → sync 4th slot (by identity); keep `is_active` as mask.
- [ ] Metrics: honest_success, traitor-caused collisions, detection / false-positive / time-to-detect.
- [ ] CTDE guard: trust uses ONLY own-LiDAR + received broadcasts; NEVER the ground-truth traitor label.

### Training
- [ ] M1 (trust OFF): transfer `comm8_lidar`, traitors on, trust slot = 0.
- [ ] M2 (trust ON): transfer `comm8_lidar`, traitors on, trust active.
- [ ] Curriculum: 0 → 1 → 2 traitors; mild → strong deception.

### Eval
- [ ] M0 zero-shot vs traitors (vulnerability reference).
- [ ] **M1 vs M2** headline: f ∈ {1,2,3}, densities {0.20,0.30}, deterministic, fixed counting, paired seeds.
- [ ] Re-run leakage test on M2 actor.
- [ ] Plot `trust[i][traitor](t)` for one episode (qualitative proof the detector fires).

---

## 8. Citations (verify before final use)

**Artificial Immune Systems / Danger Theory:**
- Negative Selection Algorithm — A Review (arXiv:2105.06109)
- Aickelin & Cayzer, The Danger Theory and Its Application to AIS (arXiv:0801.3549)
- Multi-Agent AIS (MAAIS) for Intrusion Detection — artificial T-cell agents (Springer)

**Resilient / Byzantine MARL & multi-robot (from the review):**
- "Resilient Multiagent RL With Function Approximation" — (2H+1)-robust, W-MSR trimming
- "Following Leaders in Byzantine Multirobot Systems" — n−2f reachability, blockchain registry
- "H₂ Resilient Consensus Control Under Deception Attack" — deception attack model
- "MIR³ robust MARL" — robustness by regularization (no explicit adversary training)
- "RTE Trust Evaluation (IoV)" — multi-factor / persistent trust aggregation
- "Fault Detection via Behavioral Outlier Detection" — decentralized, immune-inspired, sliding-window behavior

**Limited-range comm (UWB) for the comm-channel claim:**
- Land & Localize — UWB nano-drone swarm (arXiv:2307.10255)
- Onboard Ranging-based Relative Localization (arXiv:2003.05853)

---

## 9. Summary answers

1. **8.0m justified?** Yes — flat region (empirical) + active constraint + comm<LiDAR safety design +
   **comm ≤ LiDAR required for verifiable trust** (the decisive Phase C reason).
2. **Is "trust OFF" the Phase B model?** No (for the headline). Phase B `comm8_lidar` is the **transfer
   base** and a **zero-shot vulnerability reference**. The fair **"trust OFF" is M1** — retrained with
   traitors but trust disabled. Headline = **M1 vs M2**.
3. **Trust mechanism:** persistent identity-indexed table (immune memory) → cross-check comm vs LiDAR
   (fast-rise/slow-decay) → retain when unverifiable → expose via the sync 4th slot → response learned by RL.

---

# NOTES / QUESTIONS FOR CLAUDE
-
-
