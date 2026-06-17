# OPTION 2 — Make Communication Actually Matter (highest upside)

**Created:** 2026-06-16 · **Risk:** MEDIUM-HIGH · **Effort:** HIGH (re-architect + retrain) · **Ceiling:** good conference.
**One-line:** *"In a partially-observable swarm where local sensing is insufficient, learned inter-agent
communication is load-bearing — we show when comm helps, by how much, and how a trust mechanism protects it."*

## Why this is the most scientifically valuable option
The reason comm was inert in Phase B is now KNOWN: each drone already gets (a) a **global Dijkstra routed
heading** (`obs[2:4]`, `swarm_env_step_B10_8_0m.py:435`) and (b) **12 m LiDAR**. Between them the drone has
complete info → comm is redundant. **Remove/weaken those crutches and comm becomes necessary.** Learning-to-
communicate MARL (CommNet, TarMAC, IC3Net) is a respected area with real venues.

## THE FEASIBILITY PROBE FIRST (cheap, ~1 day, do BEFORE committing)
Do NOT redesign blindly. First prove comm *can* be made load-bearing:
1. Take M0's env; **cripple local info**: short LiDAR (e.g., 3-4 m) + occlusion, AND replace the Dijkstra heading
   with only the raw goal coordinate (or give the goal to only SOME drones — "scout" drones that must relay it).
2. Eval the EXISTING policy with comm ON vs comm OFF under this crippled sensing.
   - If comm-ON >> comm-OFF (large gap) → comm is now load-bearing → Option 2 is viable → redesign + retrain.
   - If gap is small → comm still can't be made to matter here → fall back to Option 1.

## If the probe passes — the build
- **New env variant** (clone B10_8_0m): partial observability (short/occluded LiDAR), no Dijkstra heading (goal
  coord only, or relayed-goal), keep the 8 m comm channel.
- **Train a comm-aware policy** (transfer or fresh). Headline ablation: **comm-ON vs comm-OFF** success gap (the
  "comm matters" proof). Optionally a learned/differentiable message instead of raw pos/vel.
- **Then the adversarial angle is revived for free:** if comm is load-bearing, **deception is no longer inert** →
  a traitor's false broadcasts now hurt → the **T-Cell trust mechanism** (PHASE_C_TRUST_DESIGN.md) has a real job
  (detect + down-weight lying neighbors). Headline: clean vs deception vs deception+trust.

## Honest risks
- Big effort: new env dynamics + retraining + tuning (weeks, multiple `train_comm.py`-scale runs ~50 min each).
- Even after redesign, a clean large comm benefit is not guaranteed — the probe de-risks this but doesn't promise it.
- Competitive field; needs a clear, well-ablated story to stand out.

## Honest odds (if probe passes and comm benefit is clean)
Good conference / solid journal plausible (~50-70%); top-tier possible if the trust-under-deception result is strong.

---

## PROMPT FOR A NEW CHAT (copy the box)
```
PROJECT: TA-MAPPO — resilient drone-swarm MARL (10 drones, 20x20m), CTDE PPO (SB3), PettingZoo. Dir D:\Swarm\BTP.
Python by full path: $py = "C:\Users\Srinivasa\miniconda3\envs\swarm_rl\python.exe".

GOAL: make COMMUNICATION load-bearing (Option 2), then revive the deception/trust story. Highest-upside path.

KEY DIAGNOSIS (verified in code): comm was inert in Phase B because each drone already gets a GLOBAL Dijkstra
routed heading (obs[2:4] = get_shortest_path_direction, swarm_env_step_B10_8_0m.py:435,:98) PLUS 12 m LiDAR ->
local info is already complete -> comm is redundant. To make comm matter, REMOVE the Dijkstra heading and DEGRADE
LiDAR so drones must rely on neighbors.

STEP 1 (FEASIBILITY PROBE FIRST, no training): clone an eval; cripple sensing (LiDAR 3-4 m + occlusion; replace
Dijkstra heading with raw goal coord OR give goal to only some "scout" drones); eval the existing model M0
(models/apex_ultra_glide_v14_comm8_lidar_final.zip) with comm ON vs comm OFF.
  comm-ON >> comm-OFF  -> comm is load-bearing -> proceed to redesign+retrain.
  small gap            -> comm can't be made to matter here -> tell me, switch to Option 1 (limit paper).

STEP 2 (if probe passes): build a new env variant (partial obs, no Dijkstra heading, keep 8 m comm), retrain a
comm-aware policy, headline ablation comm-ON vs comm-OFF. Then revive deception: false broadcasts now hurt ->
add the T-Cell trust mechanism (PHASE_C_TRUST_DESIGN.md), headline clean vs deception vs deception+trust.

INVARIANTS: env swarm_env_step_B10_8_0m.py (params: communication_range, congestion_mode, target_density);
load PPO.load(path, custom_objects={"policy_class": MAPPO_Policy_B5}, device="cpu") with MAPPO_Extractor_B5
(actor f[:, :130], critic f[:, 130:], vf dim 520) copied from probe_ram_oracle_smart.py; obs(650): vel[0:2]
goaldir[2:4](DIJKSTRA) goaldist[4] yaw[5] LiDAR[6:54] neighbors[54:99] congestion[99] sync[100:120] traj[120:130]
global[130:650]; honest_success = reached/(n-f); densities [0.20,0.30]. Training pattern: train_comm.py (~50 min/run).

READ: PHASE_C_TRUST_DESIGN.md, PHASE_C_REFINEMENTS.md, MODEL_LEAK_LEDGER.md, CTDE_LEAKAGE_INVESTIGATION.md,
PHASE_B_CONCLUSIONS.md.

RULES: probe BEFORE building (we've had 4 bounded-angle surprises); no hallucination; no guessed numbers; verify
code (watch stale __pycache__); honest_success excludes traitors.

START: build STEP 1 (the crippled-sensing comm ON-vs-OFF probe) and report the gap before any redesign. No guessing.
```
