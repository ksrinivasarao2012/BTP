

# Phase C — Final Try: the two UNTESTED defense classes (oracle-first)

**Date:** 2026-06-16 · **Run AFTER:** clean re-runs + 200-map ceiling confirmation.
**Why:** the paper needs more than characterization to aim high. We have ruled out only ONE of three defense
classes. This plan tests the other two **with oracles first (no training)** — the same discipline that caught
3 dead ends. **Win-win:** a defense that clears the bar → a real contribution to build; both fail → an
ironclad, theory-backed fundamental-limit result. Refs: `MODEL_LEAK_LEDGER.md`, `PATH_B_ANALYSIS_PAPER.md`.

Env python: `& "C:\Users\Srinivasa\miniconda3\envs\swarm_rl\python.exe" <script>`
Model M0: `models/apex_ultra_glide_v14_comm8_lidar_final.zip` · densities [0.20,0.30] · congestion=lidar.
References: M0 ram f=2 = **77.4/73.5** · evasion oracles **~75-80%** · baseline (no rammer) **95.6/91.1**.

---

## The three defense classes (status)

| Class | Idea | Status |
|---|---|---|
| **Evasion** | the targeted drone dodges | ✅ tested → **RULED OUT** (~80% ceiling, `probe_ram_oracle*.py`) |
| **Coordination** | healthy teammates body-block / screen the rammer | ❌ **untested → TEST 1** |
| **Speed asymmetry** | the targeted drone gets an emergency speed burst | ❌ **untested → TEST 2** (theory-backed) |

**Pursuit-evasion theory (the spine of the framing):** for a pursuer and evader of *equal* max speed on a
pure-pursuit course, interception is geometrically achievable → evasion can't guarantee escape (matches our
oracle). But if the evader's max speed exceeds the pursuer's, the pursuer **cannot** close the gap → escape is
guaranteed. So **speed asymmetry is a principled, near-certain defense**, and coordination is the open
empirical question. This connects the result to classical theory regardless of outcome.

---

## TEST 1 — Coordination oracle  (`probe_coord_oracle.py`, ~half day, no training)

**Build:** clone `probe_ram_oracle_smart.py`; keep everything (load M0, env, rammers `traitor_behavior="ram"`,
honest_success metric, seeds, solvable gate, `finished` set). **Change only the honest-action rule:**
- Each step, for each rammer, find the honest drone it is currently targeting (its nearest active honest drone
  = `_ram_action` target). Call it the **victim**.
- Find the **nearest healthy drone to the rammer that is NOT the victim** = the **blocker**.
- Override the blocker's action to **interpose**: steer toward the midpoint between rammer and victim (a point
  ~`BLOCK_GAP=0.5 m` in front of the rammer on the rammer→victim line). All other honest drones: policy action.
- Everyone keeps the policy's obstacle avoidance (blend: `clip(policy_act + W*interpose_unit, -1, 1)`).

**Decision rule (print it):**
- coord oracle **> ~85%** → coordination recovers success → **BUILD** a learned screening defense (real contribution).
- coord oracle **~80%** (≈ evasion oracle) → **RULED OUT**; the blocker just trades itself for the victim.

**Honest prior:** uncertain. Body-blocking may save the victim but expose the blocker (net honest_success flat).
The oracle settles it cheaply.

**Run:** `& $py probe_coord_oracle.py 2 models\apex_ultra_glide_v14_comm8_lidar_final.zip 30` (then 200).
Output: `results/phase_c_probe/oracle_coord_f2.csv`.

---

## TEST 2 — Speed-asymmetry oracle  (`probe_speed_oracle.py`, ~half day, no training)

**Needs a tiny env hook** (one attribute, not a behavior change):
- In `swarm_env_step_B10_8_0m`, add `self.speed_boost = {}` (default empty) in `__init__`, and in `step()` where
  the action is scaled by `self.max_velocity`, use `self.max_velocity * self.speed_boost.get(idx, 1.0)` for that
  drone. (If the code clips action then multiplies by max_velocity, multiply by the boost there.)

**Build:** clone `probe_ram_oracle_smart.py`. Each step: any honest drone with a rammer within `EVADE_DIST=2.0 m`
gets `env.speed_boost[idx] = BOOST` (try 1.3, then 1.5) and uses the LiDAR-aware `smart_escape` flee action; clear
the boost when safe. Everyone else normal.

**Decision rule:**
- speed oracle **>> ~80%** (expected, per theory) → **BUILD** an emergency-burst defense; justify the burst
  ("short over-speed under attack") and report the speed cost.
- if it does **not** help → escape is limited by obstacles/geometry, not speed → strengthens the limit result.

**Run:** `& $py probe_speed_oracle.py 2 models\apex_ultra_glide_v14_comm8_lidar_final.zip 1.3 30` (boost arg).
Output: `results/phase_c_probe/oracle_speed_f2_b1.3.csv`.

---

## What each outcome gives the paper

| Outcome | Paper becomes |
|---|---|
| TEST 1 or TEST 2 clears ~85% | **Working trust-aware physical defense** (oracle-validated → trained M2). Strong contribution. |
| Both fail | **Fundamental-limit result, theory-backed:** decentralized swarms cannot defend an equal-speed physical adversary by evasion OR coordination; only speed/role asymmetry breaks it (pursuit-evasion). Principled negative result. |

Either is a real step up from pure characterization.

---

## STEP 3 — If an oracle clears the bar: build the learned defense (M2)
- Add the chosen mechanism to obs/dynamics; transfer from M0; curriculum with rammers (and a false-alert
  traitor if using the comm threat-share variant). Headline: M1 (no defense) vs M2 (defense) at f=1,2,3.
- This is exactly the build path in `PATH_A_COORDINATION_DEFENSE.md` §3 — revived ONLY for whichever class passed.

## Honest caveats (keep us disciplined)
- No guarantee of publication; this is the highest-leverage addition, not a promise.
- Oracles are upper bounds (true positions) — they bound *feasibility*, not deployability.
- Speed asymmetry changes the physics → must be justified and its cost reported; don't hide it.
- Test before building. If both oracles fail, do NOT train a defense — write the limit paper.

## Sequence
1. ☐ finish clean re-runs + fill Phase B tables (`LEAK_REMEDIATION_LOG.md`)
2. ☐ confirm ceiling 200 maps: `& $py probe_ram_oracle_smart.py 2 models\apex_ultra_glide_v14_comm8_lidar_final.zip 200`
3. ☐ TEST 1 coordination oracle  →  ☐ TEST 2 speed-asymmetry oracle
4. ☐ if a test passes → build M2; else → write the limit paper
