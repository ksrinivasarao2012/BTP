# OPTION 1 — Fundamental-Limit / Characterization Paper (the safe floor)

**Created:** 2026-06-16 · **Risk:** LOW · **Effort:** LOW (most data in hand) · **Ceiling:** workshop / mid-tier IEEE.
**One-line:** *"A sensing-grounded MARL swarm is immune to communication attacks but provably vulnerable to a
physical (ramming) adversary; we characterize the threat and bound the defense ceiling."*

## Why this is the floor
Almost everything is already measured on the clean model M0. It is honest and rigorous. Its weakness is low
novelty (no new method) and a largely *negative* result — so aim it at a workshop or a mid-tier/IEEE venue,
not a top conference.

## The honest scientific spine
1. Navigator: CTDE PPO, 10 drones, 95.55/91.10 success (d=0.20/0.30).
2. **Robust to comm attacks:** deception (false pos/vel) inert; range/blackout ~flat (−5-8 pp). LiDAR overrides.
3. **Vulnerable to physical adversary:** ram costs ~−9 pp/rammer; f=2 = 77.4/73.5.
4. **Defense ceiling is fundamental:** evasion oracle ~75-80 % (and coordination/speed oracles, once run, give the
   final bound). Pursuit-evasion theory explains it: equal-speed pursuer can intercept; only speed/role asymmetry breaks it.

## TWO disclosures you MUST make (or a reviewer kills the paper)
- **8 m communication model** — drones share pos/vel within 8 m, perfect/zero-latency (see `CTDE_LEAKAGE_INVESTIGATION.md`).
- **Dijkstra goal-direction** — `obs[2:4]` is the gradient of a global Dijkstra shortest-path map
  (`swarm_env_step_B10_8_0m.py:435`, `:98`). This is a *privileged, map-aware* heading. Frame it honestly as
  "an external mission planner provides routed waypoints; the policy handles local control + collision avoidance."
  It does NOT undermine the ram-vulnerability result (orthogonal to path guidance), but it must be stated.

## What's left to do
- Fill the clean Phase-B tables (`LEAK_REMEDIATION_LOG.md` §6) from the clean re-runs.
- Confirm ram ceiling at 200 maps; finish coordination + speed oracles (`PHASE_C_FINAL_TRY_PLAN.md`).
- Add ≥1 baseline (ORCA) and the comm-noise robustness result.
- Write per `PATH_B_ANALYSIS_PAPER.md` §4 structure. Cite ONLY `results/clean/*` and `results/phase_c_probe/*`.

## Honest odds
Workshop ~65-80 %; mid-tier/IEEE ~45-65 % with a baseline + clean writing; top-tier ~10-20 %.

---

## PROMPT FOR A NEW CHAT (copy the box)
```
PROJECT: TA-MAPPO — resilient drone-swarm MARL (10 drones, 20x20 m), CTDE PPO (SB3), PettingZoo. Dir D:\Swarm\BTP.
Python by full path: $py = "C:\Users\Srinivasa\miniconda3\envs\swarm_rl\python.exe".

GOAL: write the FUNDAMENTAL-LIMIT / characterization paper (Option 1). Honest, rigorous, workshop/mid-tier target.

STATE (all on CLEAN model M0 = models/apex_ultra_glide_v14_comm8_lidar_final.zip; baseline 95.55/91.10):
- Comm deception inert (~0pp); range/blackout ~flat (-5-8pp) -> robust to comm attacks.
- Physical ramming is the threat: ~-9pp/rammer; f=2 = 77.4/73.5.
- Evasion oracle capped ~75-80% (coordination + speed oracles give the final bound; see PHASE_C_FINAL_TRY_PLAN.md).
- Pursuit-evasion theory explains the limit.

MUST DISCLOSE (both are privileged-but-modeled, verified in code):
- 8 m comm model (perfect/zero-latency). See CTDE_LEAKAGE_INVESTIGATION.md.
- Dijkstra goal-direction: obs[2:4] = gradient of a GLOBAL Dijkstra shortest-path map (swarm_env_step_B10_8_0m.py:435,:98)
  -> frame as "external mission planner gives routed waypoints; policy does local control". Does NOT affect the ram result.

INVARIANTS: env swarm_env_step_B10_8_0m.py; load PPO.load(path, custom_objects={"policy_class": MAPPO_Policy_B5},
device="cpu") with MAPPO_Extractor_B5 (actor f[:, :130], critic f[:, 130:], vf dim 520) copied from probe_ram_oracle_smart.py;
honest_success = reached/(n-f); densities [0.20,0.30]; congestion=lidar; comm=8.0.

READ: PATH_B_ANALYSIS_PAPER.md, PHASE_CD_PATHS_A_AND_B.md, PHASE_C_PROBE_RESULT.md, LEAK_REMEDIATION_LOG.md,
MODEL_LEAK_LEDGER.md, results/clean/*, results/phase_c_probe/*.

RULES: no hallucination; no guessed numbers; verify code before asserting; cite only clean results.

START: read PATH_B_ANALYSIS_PAPER.md, confirm state, then help me (1) finish the remaining clean runs/oracles,
(2) add an ORCA baseline, (3) draft the paper. No guessing.
```
