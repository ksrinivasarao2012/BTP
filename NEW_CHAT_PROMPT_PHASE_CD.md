# NEW CHAT PROMPT — Phase C/D defense (the path to a real paper)

Copy everything in the box into a fresh Claude Code chat. It is self-contained (no prior history needed).

---

```
PROJECT: TA-MAPPO (Trust-Aware Multi-Agent PPO) — bio-inspired MARL for resilient drone-swarm navigation.
10 drones, 20x20 m, shared goal. CTDE PPO (Stable-Baselines3), PettingZoo ParallelEnv. Working dir D:\Swarm\BTP.
Windows / PowerShell. Run python by FULL PATH (conda activate is a no-op here):
  $py = "C:\Users\Srinivasa\miniconda3\envs\swarm_rl\python.exe"

MY GOAL FOR THIS CHAT:
Phase B is done and clean. A pure Phase-B "analysis/characterization" paper (Path B) is only a weak
workshop/mid-tier result. I want the **Phase C/D adversarial defense to be the real contribution** that lifts
this to a stronger venue. Help me DESIGN and EXECUTE that defense — rigorously, evidence-first, no guessing.

WHERE WE ARE (all established on the CLEAN model — trust these, don't re-derive):
- Clean model M0 = models/apex_ultra_glide_v14_comm8_lidar_final.zip  (8 m gated comm + LiDAR congestion).
  CTDE-clean: actor ignores global block (0.0%) and neighbor stagnation (0.2%); uses LiDAR + 8 m comm only.
  Baseline (no adversary) honest_success = 95.55% (d=0.20) / 91.10% (d=0.30).
- Phase C/D findings (probes on M0, honest_success = reached/(n-f), traitors excluded):
  * Communication DECEPTION (false position/velocity broadcasts) is INERT (~0 pp): LiDAR overrides lies.
  * Physical RAMMING is the real threat: ~ -9 pp per rammer. f=2 honest_success = 77.4 / 73.5.
  * Retraining vs rammers (M1 = models/apex_ultra_glide_M1_ram_final.zip) barely helps (+1-3 pp).
  * EVASION oracle (perfect-info dodge, even LiDAR-aware) caps at ~75-80% -> EVASION IS RULED OUT.

THE OPEN OPPORTUNITY (why a paper is still possible):
We tested only ONE of three defense classes. Two remain UNTESTED:
  (A) COORDINATION — healthy teammates body-block / screen the rammer to protect a target.
  (B) SPEED ASYMMETRY — targeted drone gets a short emergency speed burst. THEORY-BACKED: by pursuit-evasion
      geometry an equal-speed pursuer can always intercept, but a faster evader CANNOT be caught.
Plan in PHASE_C_FINAL_TRY_PLAN.md. WIN-WIN: if an oracle for (A) or (B) beats ~85% -> build & train a learned
trust-aware defense (M2) = real contribution. If BOTH fail -> we have a theory-backed FUNDAMENTAL-LIMIT result
(decentralized swarms can't defend an equal-speed physical adversary by evasion or coordination) = a principled
paper either way.

WHAT I WANT YOU TO DO (in order, oracle BEFORE build):
1. Build & run the COORDINATION oracle (probe_coord_oracle.py) per PHASE_C_FINAL_TRY_PLAN.md TEST 1. Decide.
2. Build & run the SPEED-ASYMMETRY oracle (probe_speed_oracle.py + a tiny env speed_boost hook) per TEST 2. Decide.
3. If either clears ~85%: design + train the learned defense M2 (transfer from M0; curriculum with rammers;
   headline = M1 no-defense vs M2 defense at f=1,2,3). If using a comm threat-share variant, add a false-alert
   traitor + the T-Cell trust mechanism (PHASE_C_TRUST_DESIGN.md) so the "Trust-Aware" title is earned.
4. If both fail: help me write the fundamental-limit paper (pursuit-evasion framing).

KEY INVARIANTS (must respect):
- Env: swarm_env_step_B10_8_0m.py. Hooks present & verified: traitor_indices(set);
  traitor_behavior in {"navigate","ram"}; deception_mode in {"none","false_velocity","false_position"};
  _ram_action(idx) (full-throttle toward nearest active honest drone); _falsify_broadcast(...).
  Use communication_range=8.0, congestion_mode="lidar".
- Load model EXACTLY: PPO.load(path, custom_objects={"policy_class": MAPPO_Policy_B5}, device="cpu")
  with MAPPO_Extractor_B5 (policy_net on f[:, :130]; value_net on f[:, 130:]; vf input dim 520).
  Copy both classes verbatim from probe_ram_oracle_smart.py.
- Obs (650): vel[0:2] goaldir[2:4] goaldist[4] yaw[5] LiDAR[6:54] (sector min = obs[6:22]*12 m)
  neighbors[54:99] (9x{rel_pos2,vel2,active1}) congestion[99] sync[100:120] (5x{rel_vel2,stagnation1,pad=0})
  trajectory[120:130] global/critic[130:650].
- Eval pattern (match the repo's normal scripts): obs_dict,_ = env.reset(seed=..., options={"spawn_mode":"clustered"});
  gate on env._is_map_solvable; batch model.predict over active agents; env.step({a:act}); use a `finished` set
  to avoid double-counting; seed = 900_000_000 + int(density*100)*10_000 + map_idx + attempts*5_000.
- Existing probes to clone: probe_ram.py, probe_deception.py, probe_ram_oracle.py, probe_ram_oracle_smart.py.

READ THESE FIRST (they hold the C/D record):
  PHASE_C_FINAL_TRY_PLAN.md (the two oracle specs + decision rules + pursuit-evasion framing)  <- primary
  PHASE_CD_PATHS_A_AND_B.md (consolidated evidence table)
  PHASE_C_PROBE_RESULT.md (deception-inert result)
  PHASE_C_DEFENSE_PLAN.md, PHASE_C_TRUST_DESIGN.md, PHASE_C_REFINEMENTS.md (defense + trust design)
  MODEL_LEAK_LEDGER.md / CTDE_LEAKAGE_INVESTIGATION.md (why M0 is the clean model to use)
  raw data: results/phase_c_probe/*.csv

RULES (hard): no hallucination; no guessed/fabricated numbers; VERIFY code before asserting (watch stale
__pycache__/.pyc); probe/oracle BEFORE building (we've had 3 bounded-angle surprises — evasion was the latest);
honest_success excludes traitors; don't use the API past my limit.

START BY: reading PHASE_C_FINAL_TRY_PLAN.md, confirming the state above matches the repo, then build TEST 1
(coordination oracle). Tell me the decision (beats ~85% or not) before building anything else. No guessing.
```

---

## Notes (for you, not the new chat)
- This prompt commits the new chat to the **evidence-first defense path**: oracle → (only if it clears the bar) train.
- Honest expectation to keep in mind: of the two untested classes, **speed-asymmetry is the most likely to work**
  (it's geometry), but it changes the physics so it must be justified ("emergency burst") and its cost reported.
  **Coordination is genuinely uncertain.** If both fail, the limit paper is the fallback — still a real paper.
- Everything the new chat needs is in the repo; it does not need this conversation's history.
