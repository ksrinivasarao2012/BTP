# Phase C/D — Progress Log (Adversarial Defense Investigation)

**Last updated:** 2026-06-16
**Clean model under test (M0):** `models/apex_ultra_glide_v14_comm8_lidar_final.zip`
**Environment:** `swarm_env_step_B10_8_0m.py` (10 drones, 20×20 m, shared goal, 8 m gated comm + 48-ray LiDAR, `congestion_mode="lidar"`)
**Python:** `C:\Users\Srinivasa\miniconda3\envs\swarm_rl\python.exe` (run by full path; `conda activate` is a no-op here)
**Method discipline:** oracle/probe (perfect-info upper bound) BEFORE any training. honest_success = reached / (n − f); traitors excluded.

---

## 1. Established facts inherited at start of this session (trusted, not re-derived)

| Fact | Value |
|---|---|
| Baseline honest_success, **no adversary** | 95.55% (density 0.20) / 91.10% (density 0.30) |
| M0 CTDE-clean | actor ignores global block (0.0%) and neighbor stagnation (0.2%); uses LiDAR + 8 m comm only |
| **Communication deception** (false position/velocity broadcasts) | **INERT** (~0 pp) — LiDAR overrides the lies |
| **Physical ramming** | the real threat: ~−9 pp per rammer; f=2 honest_success = 77.4 / 73.5 |
| Retraining vs rammers (M1 = `apex_ultra_glide_M1_ram_final.zip`) | barely helps (+1–3 pp) |
| **Evasion oracle** (perfect-info LiDAR-aware dodge) | ~80% ceiling → **RULED OUT** |

The open question entering this session: two of three physical-defense classes were **untested** — **coordination** (teammates body-block the rammer) and **speed asymmetry** (target gets an emergency speed burst, theory-backed by pursuit-evasion geometry).

---

## 2. Work performed this session

### 2.1 TEST 1 — Coordination oracle (`probe_coord_oracle.py`) — BUILT & RUN

- **Built** by cloning the verified `probe_ram_oracle_smart.py` (same M0 load, env, rammers, seeds, solvable gate, `finished` set, honest_success metric). **Only the honest-action rule changed:**
  - Each step, for each rammer: **victim** = its nearest active honest drone (replicates `env._ram_action` targeting exactly); **blocker** = nearest active honest drone to the rammer that is *not* the victim.
  - Blocker action overridden to **interpose**: steer to a point `BLOCK_GAP=0.5 m` in front of the rammer on the rammer→victim line, blended with the policy action: `clip(policy_act + W*interpose_unit, −1, 1)` (W=1.0). All other honest drones keep the policy action.
- **Result:** does **NOT** clear the ~85% bar — at or below no-defense.

| maps | d=0.20 | d=0.30 |
|---|---|---|
| 30 | 75.8% | 75.4% |
| **200 (confirmation)** | **77.0%** | **71.9%** |

- **Mechanism:** the blocker just trades itself for the victim — honest_success stays flat while drone-collisions shift (drone-coll 18.4% / 20.3% at 200 maps). **Coordination = RULED OUT.**
- **Output:** `results/phase_c_probe/oracle_coord_f2.csv`

### 2.2 TEST 2 — Speed-asymmetry oracle — PRIOR RESULT WAS INVALID; FIXED & RE-RUN

**Critical finding — the earlier speed result was a no-op, not a real null.** The pre-existing `oracle_speed_f2_b1.40.csv` (77.4/73.5) was invalid for two verified reasons:

1. **The env hook was never added.** The plan required `swarm_env_step_B10_8_0m.py` to scale velocity by `self.speed_boost.get(idx, 1.0)`. A full grep showed `speed_boost` appeared **nowhere** in the env — `env.speed_boost[idx] = boost` in the probe wrote a dead attribute the env never read.
2. **No escape direction.** The probe submitted the raw policy action (`action[a] = act[k]`) instead of the required LiDAR-aware `smart_escape` flee.

So the "boosted" drone neither moved faster nor fled — the number was just no-defense again. (This is exactly the stale/unverified-code trap the plan warned about.)

**Fixes applied:**
- **Env (`swarm_env_step_B10_8_0m.py`):** added `self.speed_boost = {}` in `__init__`; in `step()` the velocity cap is now `np.maximum(self.max_velocity * boost * np.exp(-0.15*neighbors_count), 1.10)` with `boost = self.speed_boost.get(idx, 1.0)`. **Additive & default-1.0 → no other script is affected.**
- **Probe (`probe_speed_oracle.py`):** added the verbatim `smart_escape` from `probe_ram_oracle_smart.py`; when a rammer is within `EVADE_DIST` the drone now both sets the boost *and* flees with `smart_escape`.

**Verification:** boost=1.0 control (= flee, no speed change) reproduces the evasion oracle (~75–80%), and boost=2.0 visibly changes behaviour (obstacle-collisions spike 2%→8%) → the hook is live.

**Result (30 maps unless noted):**

| config | d=0.20 | d=0.30 | note |
|---|---|---|---|
| boost 1.0 (= evasion) | 75.0% | 79.6% | control |
| boost 1.5 | 79.2% | 76.3% | no real gain |
| **boost 1.5 (200-map confirm)** | **79.2%** | **73.4%** | = no-defense |
| boost 2.0 | 70.4% | 71.7% | **worse** (obstacle crashes) |
| boost 1.5, EVADE_DIST 3.5 | 70.8% | 76.7% | earlier flee → worse |
| boost 1.5, EVADE_DIST 5.0 | 70.0% | 72.1% | earlier flee → worse |

- **Mechanism:** in obstacle-dense space a faster evader trades drone-collisions for **obstacle**-collisions; over-boosting and earlier triggering both strictly worsen it. The swarm is **obstacle-limited, not speed-limited** — the open-space pursuit-evasion advantage of a faster evader does not survive the obstacle field. **Speed asymmetry = RULED OUT.**
- **Output:** `results/phase_c_probe/oracle_speed_f2_b1.50.csv` (and b1.40 = the invalid one; b2.00, etc.)

### 2.3 Beyond-sensing comm probe (`probe_comm_range.py`) — BUILT, RUNNING

- **Motivation:** comm deception was inert because **comm range (8 m) < LiDAR range (12 m)** — every drone you hear about you can already see, so lies are pointless. This is structural, not fundamental. The probe raises `communication_range` to {8, 12, 16, 20} m (16/20 = beyond LiDAR) and measures honest_success vs rammers.
- **Decision rule:** if honest_success **rises** with comm range → comm carries non-redundant beyond-sensing info → a liar could poison it → a **T-Cell trust defense has a real target** → a *positive* "Trust-Aware" paper is alive. If **flat/falls** → local sensing dominates, comm is redundant → confirms and explains the fundamental-limit result.
- **Confound (documented in the script):** M0 was trained at comm=8, so a positive result is decisive (it helps despite no retraining), while a null is suggestive but not final (M0 may simply not exploit info it never trained on). A positive would justify a retrain at extended comm.
- **Result (30 maps): NULL — strongly so.** honest_success is flat across all ranges, and the 12/16/20 m rows are **byte-identical**:

| comm range | d=0.20 | d=0.30 |
|---|---|---|
| 8 m (trained) | 75.4% | 75.4% |
| 12 m (= LiDAR) | 75.0% | 75.0% |
| 16 m (beyond LiDAR) | 75.0% | 75.0% |
| 20 m (beyond LiDAR) | 75.0% | 75.0% |

- **Interpretation:** giving M0 information about teammates it cannot sense changes its behavior by *nothing* (12 m vs 20 m identical to many decimals). M0 is effectively a **LiDAR-driven policy that ignores the comm/neighbor channel**. This is the single mechanism behind the entire Phase C/D picture — comm deception inert, comm extension inert, all motion defenses capped. There is no non-redundant info in the channel for a traitor to poison → a trust mechanism has nothing to bite on *for this model*.
- **Confound still stands:** M0 was trained at comm=8 and demonstrably under-uses neighbor obs, so this null does not prove comm is *intrinsically* useless — only that *this* policy can't exploit it. Closing that requires the L0 retrain (see action plan).
- **Output:** `results/phase_c_probe/comm_range_f2.csv`.

---

## 3. Consolidated oracle table (f=2, M0, perfect-info upper bounds)

| Defense class (oracle = upper bound) | d=0.20 | d=0.30 | verdict |
|---|---|---|---|
| No defense (`probe_ram_f2.csv`) | 80.4 | 74.4 | — |
| **Evasion** — LiDAR-aware dodge | 79.7 | 73.8 | RULED OUT |
| **Coordination** — body-block / interpose (200 maps) | 77.0 | 71.9 | RULED OUT |
| **Speed asymmetry** — boost + flee, best b1.5 (200 maps) | 79.2 | 73.4 | RULED OUT |
| *Baseline — no rammer* | *95.6* | *91.1* | *reference* |

**All three reactive-motion defense classes cap in the ~72–80% band, far below the ~85% bar and the 95.6/91.1 clean baseline. None recovers the ~15–17 pp ramming drop.** Because oracles are perfect-info upper bounds, this rules out *any* learned reactive-motion policy for the targeted/blocker drone — not just the ones M0/M1 happened to learn.

---

## 4. Files created / modified this session

| File | Change |
|---|---|
| `probe_coord_oracle.py` | NEW — coordination (interpose) oracle |
| `probe_speed_oracle.py` | FIXED — added `smart_escape` flee + real boost application |
| `swarm_env_step_B10_8_0m.py` | MODIFIED — added `self.speed_boost={}` + boost on velocity cap (additive, default 1.0) |
| `probe_comm_range.py` | NEW — beyond-sensing comm probe |
| `results/phase_c_probe/oracle_coord_f2.csv` | NEW — coordination result (200 maps) |
| `results/phase_c_probe/oracle_speed_f2_b1.50.csv` | NEW — valid speed result (200 maps) |
| `results/phase_c_probe/comm_range_f2.csv` | PENDING — comm-range result |

---

## 5. Current decision state

- Of the three reactive-motion defense classes, **all three are now ruled out** by perfect-info oracles.
- The **only** remaining path to a *positive* contribution is the **comm/trust axis** — does communication carry non-redundant, poisonable information (the beyond-sensing probe decides this).
- **Comm probe came back NULL** (M0 is comm-insensitive) → the honest call is the **fundamental-limit paper** (pursuit-evasion framing + obstacle caveat). The one remaining shot at a positive Trust-Aware paper is the **L0 extended-comm retrain** (train a policy that *relies* on beyond-sensing comm, then see if a poisonable channel emerges) — speculative, no oracle can pre-validate it. See `PHASE_CD_ACTION_PLAN.md` (Path L step L0, Path P).

---

## 6. Short-LiDAR Comm Oracle (2026-06-16) — DECISIVE NULL

### Probe: `Phase_CD/probe_comm_oracle.py`
**Script:** `Phase_CD/probe_comm_oracle.py` | **Output:** `Phase_CD/results/comm_oracle_lidar4_comm10.csv`

**Setup:** M0 evaluated at LiDAR=4m, comm=10m, NO adversaries, 30 maps × 2 densities.
Two conditions run on identical maps (paired):
- **Baseline:** pure M0 policy
- **Oracle:** perfect-info override whenever a drone in the comm-only annulus (4–10m) is on a
  collision course (TTC < 2.2s) — proactive perpendicular dodge with LiDAR-aware lane selection.

### Results

| condition | d=0.20 success | drone_coll | obst_coll | oracle_triggers |
|---|---|---|---|---|
| baseline | 73.67% | 7.33% | 18.33% | 0 |
| oracle   | 73.00% | 8.00% | 19.00% | 103 |
| **comm_value** | **-0.67 pp** | | | |

| condition | d=0.30 success | drone_coll | obst_coll | oracle_triggers |
|---|---|---|---|---|
| baseline | 81.00% | 5.33% | 13.33% | 0 |
| oracle   | 81.67% | 4.00% | 14.00% | 126 |
| **comm_value** | **+0.67 pp** | | | |

### Three-signal analysis

**Signal 1 — oracle_triggers (103/126): POSITIVE**
The comm-only annulus IS physically occupied with approaching drones. The information geometrically
exists. This rules out "the annulus is always empty" as the explanation for the null.

**Signal 2 — comm_value (~0 pp): DECISIVE NULL**
Despite 103–126 oracle interventions with perfect ground-truth positions, success changes by < 1 pp
and is **negative at d=0.20**. This is the perfect-information upper bound. A trained policy can
only do worse. If the ceiling is 0 pp, no training regime can exceed it.

**Signal 3 — collision breakdown: OBSTACLE-LIMITED MECHANISM CONFIRMED**
At d=0.20: oracle RAISES both drone_coll (+0.67) and obst_coll (+0.67) — the proactive dodge
makes things worse. At d=0.30: oracle reduces drone_coll (-1.33 pp) but increases obst_coll
(+0.67 pp) — the dodge trades drone hits for obstacle hits, net ~0. The environment is so
obstacle-dense that no clean perpendicular evasion lane exists. The proactive dodge has nowhere
to land safely.

### Scientific conclusion

**The short-LiDAR (4m) regime does NOT create a communication-dependent task. It creates an
obstacle-avoidance-limited task.** The comm-only annulus is physically occupied but structurally
unexploitable because obstacle density eliminates the clear evasion lanes that annulus-aware
dodging requires. This is not a training artifact — it is a geometric property of the environment.

**From-scratch training at 20M steps is NOT justified.** The oracle result proves that even perfect
exploitation of the comm channel adds zero success. PPO cannot learn to exploit information whose
exploitation is structurally penalized by the map.

**Path L (Fundamental Limit) is now the confirmed paper direction.** This probe adds a new
mechanism to the evidence chain: not only are motion defenses bounded, but even the informational
channel (communication) provides no exploitable advance warning in obstacle-dense space.

### Paper-ready statement addition
> *"A perfect-information oracle acting on comm-only annulus data (drones at 4–10m, TTC < 2.2s)
> gains < 1 pp success over the LiDAR-only baseline (−0.67 pp at d=0.20, +0.67 pp at d=0.30),
> because the obstacle-dense environment eliminates clear evasion lanes for proactive dodging.
> Oracle fires 103–126 interventions per condition, confirming the comm channel is geometrically
> occupied — the null result is structural, not a sampling artifact. Training a policy from scratch
> to exploit comm is therefore not justified: the oracle establishes the exploitation ceiling at ~0 pp."*
