# NEW CHAT PROMPT — paste this into a fresh Claude Code chat

Copy everything in the box below into a new chat. It is self-contained (no prior history needed).

---

```
PROJECT: TA-MAPPO — resilient drone swarm (10 drones, 20x20m, shared goal), CTDE PPO (Stable-Baselines3),
PettingZoo ParallelEnv. Working dir D:\Swarm\BTP. Windows, PowerShell. Python env: run scripts via the
swarm_rl env python.exe by full path (conda activate no-ops in non-interactive shell).

WHERE WE ARE (all established with probes — do NOT re-derive, trust these):
- Communication DECEPTION is inert (~0pp at f=2,3): local LiDAR overrides lies.
- Communication range/blackout barely matters (sweep flat; blackout -5-8pp): swarm is LiDAR-grounded.
- PHYSICAL RAMMING is the real threat: ~-9pp per rammer (f1≈-9, f2≈-18, f3≈-25).
- Retraining vs rammers (M1) barely helped (+1-3pp).
- ORACLE evasion (naive 77.9/74.6 AND smart LiDAR-aware 75.0/79.6) both cap ~75-80% vs clean 95.6/91.1.
  => Local per-agent evasion CANNOT recover success; rammer imposes a fundamental ~15-20pp loss
     (turns collisions into timeouts). Defense must be GLOBAL, or we write the analysis as the result.

READ THESE FIRST (they have full detail):
  PHASE_CD_PATHS_A_AND_B.md   (overview + A-vs-B decision)
  PATH_A_COORDINATION_DEFENSE.md  (build plan: A1 comm threat-sharing + trust; A2 screening; A3 asymmetry)
  PATH_B_ANALYSIS_PAPER.md    (write-up plan; ~80% done from existing results)

KEY INVARIANTS (must respect):
- Env: swarm_env_step_B10_8_0m.py. Hooks present & verified: traitor_indices(set),
  traitor_behavior in {"navigate","ram"}, deception_mode in {"none","false_velocity","false_position"},
  _ram_action(idx), _falsify_broadcast(...). (A duplicate init block exists — harmless, last-wins.)
- Model M0 (production, CTDE-clean, 95.55/91.10): models/apex_ultra_glide_v14_comm8_lidar_final.zip
  M1 (vs rammers): models/apex_ultra_glide_M1_ram_final.zip
- Load EXACTLY: PPO.load(path, custom_objects={"policy_class": MAPPO_Policy_B5}, device="cpu")
  with MAPPO_Extractor_B5 (policy_net on f[:, :130]; value_net on f[:, 130:]; vf input dim 520).
  Copy both classes verbatim from probe_ram_oracle_smart.py.
- Obs (650): vel[0:2] goaldir[2:4] goaldist[4] yaw[5] LiDAR[6:54] (sector min = obs[6:22]*12 meters)
  neighbors[54:99] congestion[99] sync[100:120] (5×{rel_vel2,stagnation1,reserved-pad=0.0})
  trajectory[120:130] global/critic[130:650].
- honest_success = reached / (terminals excluding traitors); use a `finished` set to avoid double-counting.
- Densities [0.20,0.30]; congestion_mode="lidar"; communication_range=8.0;
  seed = 900_000_000 + int(density*100)*10_000 + map_idx + attempts*5_000; gate on env._is_map_solvable.
- Existing probes: probe_ram.py, probe_deception.py, probe_ram_oracle.py, probe_ram_oracle_smart.py.

RULES (hard): no hallucination; no guessed/fabricated numbers; VERIFY code before asserting (watch stale
__pycache__/.pyc); probe/oracle BEFORE building (we've had 3 bounded-angle surprises); don't use API past limit.

>>> MY DECISION: ____  (write ONE of:)
  "PATH A" — then do STEP 1 in PATH_A_COORDINATION_DEFENSE.md §2: build probe_threat_share_oracle.py
             (clone probe_ram_oracle_smart.py; give honest drones SHARED early knowledge of all rammer
             positions and reroute around a threat zone radius R_AVOID=3-4m, reacting earlier than the
             2m own-LiDAR trigger — this simulates comm early-warning). Run f=2, 30 maps, then 200.
             Decision: >~85% => build M2 (threat-share+trust); ~75-80% => trust/false-alert angle only.
  "PATH B" — then do PATH_B_ANALYSIS_PAPER.md §3: confirm oracle ceiling at 200 maps, add 1 baseline,
             finalize ram f=1/2/3, then draft the paper per §4 structure.

Start by reading the three .md files above, confirm the state matches, then execute my decision. No guessing.
```

---

## Notes
- The detailed plans live in the three `.md` files referenced above — they are committed in the repo root.
- If you (the user) are unsure A vs B: choose **PATH A** and run only STEP 1 (the 1-day oracle). It either
  unlocks Path A or confirms Path B — with data, not a guess.
