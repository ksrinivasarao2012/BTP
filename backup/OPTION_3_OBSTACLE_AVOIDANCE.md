# OPTION 3 — Multi-Agent Obstacle-Avoidance Paper (weakest bet — read the blocker first)

**Created:** 2026-06-16 · **Risk:** HIGH · **Effort:** MEDIUM-HIGH · **Ceiling:** hard at good venues (crowded field).
**One-line:** *"Decentralized multi-agent navigation among obstacles with learned LiDAR-based control."*

## ⚠ THE BLOCKER (verify and fix FIRST — this is why it's the weakest option)
`obs[2:4]` is the **gradient of a GLOBAL Dijkstra shortest-path map** (`swarm_env_step_B10_8_0m.py:435`, map
built in `_compute_shortest_path_distance_map`, `:98`). i.e., the policy is **handed the optimal heading that
already routes around every obstacle**. For an *obstacle-avoidance* paper this is fatal: the hard part (global
path planning) is done by Dijkstra and fed in, so you are NOT demonstrating learned obstacle avoidance — a
reviewer will reject it on sight. **You must remove the Dijkstra heading (give only the raw goal coordinate) and
RETRAIN**, then show the policy learns to find its own way around obstacles from LiDAR alone.

## The crowded-field problem (the second reason it's hard)
Decentralized multi-robot navigation/obstacle-avoidance is heavily studied with strong baselines you must beat:
ORCA / RVO, PRIMAL & PRIMAL2, GLAS, MAPPER, distributed-MAPF, and many MARL-nav papers. A 2D, 10-agent, 20x20
sim that merely "works" will not beat these. You need a **specific novel angle** (e.g., a sensing/communication
twist, a robustness property, a scalability or sim-to-real result) — otherwise it reads as incremental.

## What you'd have to do (in order)
1. **Audit privileged inputs** (not just Dijkstra): also `congestion` (now LiDAR-based, OK), neighbor pos/vel
   (8 m comm — disclose), and confirm nothing else is map-derived. Document a clean "what the actor senses" list.
2. **Remove the Dijkstra heading** → goal coordinate only; **retrain**; measure the success drop (this is the real
   difficulty of the task). Likely a large drop — that gap is the actual contribution space.
3. **Pick + run a real baseline** (ORCA at minimum; ideally a learned one) on the SAME maps/metric.
4. **Find a novel angle** that beats or complements SOTA (else there is no paper).
5. **Find venues** that accept applied multi-robot nav (IEEE conferences/journals, robotics workshops).

## Honest verdict
Only pursue if (2) yields a policy that, without the Dijkstra crutch, still navigates well AND you have a clear
angle to beat a real baseline. Otherwise this collapses into "incremental nav in a crowded field" → likely reject
at good venues. The crutch removal alone is real work with uncertain payoff.

## Honest odds
Good venue: low without a novel angle + SOTA comparison. Mid-tier/IEEE: possible if crutch removed + 1 baseline beaten.

---

## PROMPT FOR A NEW CHAT (copy the box)
```
PROJECT: TA-MAPPO — multi-agent drone navigation (10 drones, 20x20m), CTDE PPO (SB3), PettingZoo. Dir D:\Swarm\BTP.
Python by full path: $py = "C:\Users\Srinivasa\miniconda3\envs\swarm_rl\python.exe".

GOAL: assess + (if viable) build a MULTI-AGENT OBSTACLE-AVOIDANCE paper (Option 3). Be skeptical — this is the
weakest of my 3 options; tell me honestly if it's worth it.

CRITICAL BLOCKER (verified in code): obs[2:4] is the gradient of a GLOBAL Dijkstra shortest-path map
(swarm_env_step_B10_8_0m.py:435, map at :98) -> the policy is HANDED the optimal obstacle-routed heading. For an
obstacle-avoidance claim this is a fatal crutch. STEP 1 must REMOVE it (raw goal coordinate only) and RETRAIN,
then measure how well the policy navigates WITHOUT it. The current 95.55/91.10 is WITH the crutch and is not a
valid obstacle-avoidance result.

ALSO: this field is crowded (ORCA/RVO, PRIMAL/PRIMAL2, GLAS, MAPPER, distributed-MAPF). Merely "working" won't
beat SOTA; I need a NOVEL angle. Help me find one or tell me it's not worth pursuing.

STEPS:
1. Audit every actor input for privileged/map-derived info (Dijkstra heading = the main one; congestion is now
   LiDAR-based; neighbor pos/vel = 8 m comm). Produce a clean "what the actor truly senses" list.
2. Remove the Dijkstra heading (goal coord only), retrain (train_comm.py pattern, ~50 min/run), report the
   success drop -> that gap is the real task difficulty / contribution space.
3. Add a real baseline (ORCA) on the same maps + honest_success metric.
4. Search recent venues/SOTA for decentralized MARL obstacle avoidance; identify the current best to beat and a
   feasible novel angle. If none -> recommend I drop Option 3.

INVARIANTS: env swarm_env_step_B10_8_0m.py; load PPO.load(path, custom_objects={"policy_class": MAPPO_Policy_B5},
device="cpu") with MAPPO_Extractor_B5 (actor f[:, :130], critic f[:, 130:], vf dim 520) from probe_ram_oracle_smart.py;
clean model M0 = models/apex_ultra_glide_v14_comm8_lidar_final.zip; densities [0.20,0.30]; congestion=lidar.

RULES: no hallucination; no guessed numbers; verify code; if SOTA can't be beaten, SAY SO and recommend Option 1/2.

START: do STEP 1 (full privileged-input audit) and give me a brutally honest read on whether Option 3 is worth it
before any retraining.
```
