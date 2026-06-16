# PATH A — Active Defense (Build a Mechanism That Actually Helps)

**Date:** 2026-06-16 · **Status:** plan, not yet built · **Owner:** TA-MAPPO Phase C/D
**Read first:** `PHASE_CD_PATHS_A_AND_B.md` (overview + decision criteria).
**This file = the full build plan for Path A**, written so a fresh chat can execute it with no prior context.

---

## 0. Why Path A exists (the evidence wall)

| Finding | Evidence | Implication |
|---|---|---|
| Comm **deception** inert | deception probe ~0pp at f=2,3 | LiDAR overrides lies |
| Comm **range/blackout** ~flat | sweep 3-8-∞ flat; blackout −5-8pp | swarm is LiDAR-grounded |
| **Physical ram** is the threat | ram probe −9pp/rammer (f1≈9,f2≈18,f3≈25) | defend THIS |
| **Retrain (M1) barely helps** | M1 ≈ M0 (+1-3pp) | implicit evasion insufficient |
| **Oracle dodge can't recover** | naive 77.9/74.6, smart-LiDAR 75.0/79.6 | **local evasion capped ~80%** |

References: M0 ram f=2 = **77.4/73.5**; baseline no-rammer = **95.6/91.1**.
**Conclusion:** a committed equal-speed rammer imposes an **oracle-bounded ~15-20pp loss** that *local* evasion
cannot beat (it only turns collisions into timeouts). The defense must be **swarm-level**.

---

## 1. The three variants (ranked)

### A1 ★ — Communication-based threat-sharing + trust  (RECOMMENDED)
A drone that detects a rammer on its **LiDAR** broadcasts a **threat alert** (rammer position / "under attack").
Teammates use *received* alerts to (a) avoid the threat zone **before** they can see it themselves
(occluded / beyond their own LiDAR), and (b) coordinate.

**Why A1 unifies the whole project:**
- **Communication finally matters** (early/NLOS warning — the one thing LiDAR can't give). Answers "why comm?".
- **Deception matters again:** a traitor broadcasts **FALSE alerts** to herd honest drones away from goal (→timeouts).
- **Trust (T-Cell) gets a real job:** cross-check each alert against your own sensing; ignore alerts that don't
  match reality. **This is the "Trust-Aware" contribution.**

**Honest caveat:** the oracle had *perfect* info and still couldn't save a *targeted* drone. So threat-sharing
likely **won't rescue the target** — its value is (a) protecting *not-yet-targeted* drones + (b) the trust/false-alert
defense. **Frame the contribution as "trust-aware threat-sharing," not "evasion."**

### A2 — Coordination / screening
Healthy drones **body-block / interpose** between the rammer and a targeted teammate. Genuinely different from evasion.
Caveat: the blocker risks itself; net honest_success may not rise (trade one drone for another). Oracle decides.

### A3 — Asymmetry (emergency speed burst)
Targeted drone gets a temporary speed edge → an equal-speed pursuer can intercept, a faster evader cannot be caught.
Caveat: changes physics/fairness; must justify ("emergency burst"). It's the one change that *provably* breaks interception.

---

## 2. STEP 1 (do this first) — A1 threat-sharing **feasibility oracle** (1 day, no training)

**Goal:** measure the *upper bound* of comm threat-sharing. If even perfect shared threat-knowledge + reroute can't
beat ~80%, then comm-sharing can't rescue targets (expected) and the value is purely the trust story. If it *does*
beat ~80%, build the learned mechanism.

**Build `probe_threat_share_oracle.py`** (clone `probe_ram_oracle_smart.py`, change only the honest-action rule):

- Same scaffold: load M0 with `MAPPO_Policy_B5`, env `SwarmLidarEnv_StepB10_8_0m(target_density=d,
  communication_range=8.0, congestion_mode="lidar")`, `traitor_indices={0..f-1}`, `traitor_behavior="ram"`,
  `deception_mode="none"`. Densities [0.20, 0.30], honest_success = reached/(non-traitor terminals), seeds
  `900_000_000 + int(d*100)*10_000 + map_idx + attempts*5_000`, solvable-map gate, `finished` set (no double count).
- **Difference = the honest action rule.** Give EVERY honest drone the *shared* rammer set (global, early — the
  ceiling of broadcast warning), and reroute around a **threat zone** of radius `R_AVOID` (try 3.0–4.0m) around the
  *nearest* rammer **even if that rammer is beyond the drone's own LiDAR**:
  - `flee_u = unit(pos − nearest_rammer_pos)` when `dist < R_AVOID`.
  - Combine with goal pursuit so drones still progress: `action = clip(policy_act + W_FLEE*flee_u, -1,1)` (try W_FLEE=1.0),
    OR the LiDAR-clear-sector pick from `smart_escape()` but triggered at `R_AVOID` (earlier) instead of EVADE_DIST=2.0.
  - Key contrast vs the existing oracle: existing oracle reacts at **2m (own LiDAR)**; this reacts at **R_AVOID via
    shared knowledge** = simulates early warning. That extra reaction range is exactly what comm would buy.

**Decision rule (print it, like the other oracles):**
- threat-share oracle **> ~85%** → early warning genuinely recovers success → **build A1 mechanism (M2)**.
- threat-share oracle **~75-80%** (≈ smart oracle) → early warning doesn't rescue targets → A1's value is the
  **trust/false-alert** angle only; decide A1-trust-only vs Path B.

**Run:** `python probe_threat_share_oracle.py 2 models/apex_ultra_glide_v14_comm8_lidar_final.zip 30`
(quick 30-map; then 200-map to confirm). Save to `results/phase_c_probe/oracle_threatshare_f2.csv`.

---

## 3. STEP 2 (only if oracle > ~85%) — build the learned mechanism (M2)

**Observation additions (env `_observe`):** for each of the 5 sync-neighbors add:
- `threat_alert_j ∈ {0,1}` — neighbor j is broadcasting a threat (it detects a rammer on its LiDAR), AND
- reuse the **reserved sync pad slot** (`[100:120]`, currently the `reserved-pad1=0.0`) for a **per-neighbor trust score**.
Optionally a 2D "alerted threat direction" relayed from j. Keep comm_range=8.0 (alerts only propagate within range — that
is the realism that makes multi-hop/early-warning matter).

**Detection (robust, LiDAR-based — NOT comm):** a drone flags "I see a rammer" when a neighbor on its LiDAR shows
*intercept motion* (closing fast, bearing roughly constant) — robust to a lying rammer. EMA-filter velocity first
(see `PHASE_C_REFINEMENTS.md`). This boolean is what gets broadcast.

**Trust (T-Cell):** trust_j decays when j's alert contradicts the receiver's own sensing (no rammer where j claims),
recovers when consistent. Honest reroute weights alerts by trust_j → **false alerts from traitors get ignored.**

**Training (`train_M2_threatshare.py`, clone `train_ram_M1.py`):** transfer from M0; curriculum mixes
(rammers only) + (rammers + a false-alert traitor). Reward: small penalty for rerouting on a *false* alert (so it
learns to trust correctly), success/collision as usual.

**Headline experiments:**
1. M1 (no defense) vs M2 (threat-share+trust) at f=1,2,3 — honest_success.
2. **Trust ablation:** M2-with-trust vs M2-no-trust under a **false-alert traitor** (shows trust is load-bearing).
3. Detection metrics: FPR / time-to-detect (from `PHASE_C_REFINEMENTS.md`).

---

## 4. Files & invariants a fresh chat MUST respect

- **Env:** `swarm_env_step_B10_8_0m.py`. Hooks already present & verified: `traitor_indices`, `traitor_behavior`
  ("navigate"/"ram"), `deception_mode` ("none"/"false_velocity"/"false_position"), `_ram_action(idx)`,
  `_falsify_broadcast(...)`. (A duplicate init block exists — harmless, last-wins.)
- **Model load (exact):** `PPO.load(path, custom_objects={"policy_class": MAPPO_Policy_B5}, device="cpu")` with the
  `MAPPO_Extractor_B5` (policy_net on `f[:, :130]`, value_net on `f[:, 130:]`, vf input dim 520). Copy the class
  verbatim from `probe_ram_oracle_smart.py`.
- **M0 model:** `models/apex_ultra_glide_v14_comm8_lidar_final.zip` (CTDE-clean, 95.55/91.10). M1: `models/apex_ultra_glide_M1_ram_final.zip`.
- **Obs layout (650):** ego vel[0:2], goal dir[2:4], goal dist[4], yaw[5], LiDAR[6:54] (sector min = `[6:22]*12` m),
  neighbors[54:99] (9×{rel_pos2,vel2,active1}), congestion[99], **sync[100:120]** (5×{rel_vel2,stagnation1,**reserved-pad=0.0**}),
  trajectory[120:130], global/critic[130:650].
- **Metric:** honest_success = reached / (terminals excluding traitors). Use the `finished` set to avoid double-count.
- **Method discipline:** *probe/oracle before building* — we've had 3 bounded-angle surprises; don't skip the oracle.
- **User constraints:** no hallucination, no guessed numbers, verify code (watch stale `__pycache__`), don't use API past limit.

---

## 5. Path A risk & exit

Could be a 4th bounded angle → that's why STEP 1 (oracle) gates STEP 2. **Even if oracle fails, A1's trust/false-alert
defense is still a novel, defensible contribution** (it doesn't depend on raw success recovery). If the user wants
certainty/soon instead, switch to **Path B**.
