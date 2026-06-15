# ===== PASTE EVERYTHING BELOW INTO THE NEW CHAT =====

I'm continuing my BTP project **TA-MAPPO** (Trust-Aware Multi-Agent PPO) — a bio-inspired MARL
framework for resilient drone-swarm navigation. Working dir: `D:\Swarm\BTP`. Phase B is COMPLETE and
validated; I'm now in the **Combined Adversarial Phase (C+D)**. (The original split — C = deceptive
traitors, D = aggressive/physical traitors — is merged: deception proved inert, physical aggression is the
real threat, so it's one combined phase.) This prompt carries all the context.

## 0. First, read these files (they hold all decisions — do not re-derive or re-litigate)
- `CLAUDE.md` (project overview)
- `PHASE_B_CONCLUSIONS.md` (Phase B findings)
- `PHASE_C_DEFENSE_PLAN.md` (THE current plan — step-by-step actions + result boxes)
- `PHASE_C_PROBE_RESULT.md` (deception probe verdict)
- `PHASE_C_REFINEMENTS.md` (EMA velocity filter, trust auxiliary loss, detection metrics)
- `PHASE_C_TRUST_DESIGN.md` (trust spec — NOTE: its comm-deception framing is now deprecated; see §3 below)
- `PENDING_WORK_AND_ADVERSARY_DESIGN.md` (adversary taxonomy + literature)
- `PHASE_CD_TRAITOR_ATTRIBUTES_AND_TIMELINE.md`

## 1. The system (what's built)
- 10 drones, 20×20m, navigate to a shared goal. PPO (Stable-Baselines3), PettingZoo ParallelEnv.
- **CTDE**: actor uses LOCAL obs [0:130], critic uses GLOBAL [130:650]. Verified by a leakage test —
  the actor's action is provably invariant to the global block (0 change over 992 obs).
- Obs layout (130 local): [0:2] ego vel, [2:4] Dijkstra goal-direction, [4] Dijkstra goal-dist,
  [5] yaw, [6:54] LiDAR (16 sectors × min/mean/std), [54:99] 9 neighbors × {rel_pos2, abs-norm-vel2,
  is_active1}, [99] congestion, [100:120] sync (5 closest × {rel_vel2, stagnation1, RESERVED-pad1=0.0}),
  [120:130] own trajectory. Global [130:650] = all positions/vels + all LiDAR (critic only).
- Env file: `swarm_env_step_B10_8_0m.py`. LiDAR range 12m, comm range 8m.
- It has parameters: `communication_range` (default 8.0), `use_congestion`, `congestion_mode`
  ("env"|"lidar"|"comm"|"both"), and PROBE hooks: `traitor_indices`, `deception_mode`
  ("none"|"false_velocity"|"false_position"|"both"), `traitor_behavior` ("navigate"|"ram").
  Methods `_falsify_broadcast()` and `_ram_action()` exist and are unit-tested.
- **Collision logging is FIXED**: env sets `infos[agent]["collision_type"]` ("drone"/"obstacle"/"wall")
  + raw flags; evals read it. (An earlier bug attributed drone collisions to "obstacle" via pre-step
  positions — fixed.)

## 2. Phase B findings (established, with evidence)
- **Communication RANGE is irrelevant**: success flat across comm ∈ {3,5,8,∞} (≤1pp). 8m sits on the
  flat region; 8m ≤ 12m LiDAR is also required so trust signals are verifiable.
- **Communication CONTENT is only modestly used**: blackout (comm off) cost ~5–8pp; the swarm is
  **LiDAR-dominant** (drone-avoidance works from LiDAR; comm is secondary).
- **Feature importance** (eval-time ablation AND action saliency agree):
  LiDAR ≫ goal-direction > neighbors(comm) > ego-vel ≈ sync(comm) ≫ congestion ≈ trajectory.
- **Congestion is useless** (0 effect) and was a CTDE violation (ground-truth) — removed/replaced by a
  LiDAR-sourced version.
- **Production model: `models/apex_ultra_glide_v14_comm8_lidar_final.zip`** — CTDE-clean (LiDAR
  congestion), comm-enabled, **95.55% / 91.10%** at densities 0.20/0.30. This is the transfer base.

## 3. THE KEY PIVOT (decided by probes this session)
I ran zero-shot probes on the production model (no retraining, no defense):
- **Deception probe** (traitors broadcast false velocity/position; LiDAR kept true):
  honest_success drop **~0 pp** even at f=3 with both lies. → **Communication deception is INERT** —
  the swarm is LiDAR-grounded and overrides lies. (Also explains why comm range/blackout barely matter.)
- **Ram probe** (traitors physically steer to collide with nearest honest drone):
  honest_success **77.38% / 73.50%** vs baseline 95.55% / 91.10% → **~18 pp drop**, drone-collisions
  jumped to **~19%** (from ~0.4%). → **Physical aggression is the REAL threat.**

**DECISION:** Do NOT build a comm-deception trust mechanism (nothing to defend). Build a **behavioral,
LiDAR-based defense against physical adversaries (rammers)**. Frame the comm-attack robustness
(deception + jamming inert) as a *security property*; the physical defense is the active contribution.
Metric: `honest_success = reached / (n − f)` (traitors excluded; with f=2, denom=8).

## 4. The defense design (new direction)
- Threat signal is **motion-based** (not comm): a per-neighbor **threat score** from LiDAR-sensed
  relative position + inferred velocity (closing speed / time-to-collision / bearing alignment — the
  env already computes these danger signals for rewards). Feed it into the **reserved sync trust slot**
  [the 0.0 pad]; let the policy learn to **evade high-threat neighbors**.
- Use a **persistent identity-indexed table** (immune memory) so a flagged attacker stays flagged even
  when it leaves/re-enters the closest-5; expose via the sync slot by identity. Keep `is_active` as the
  presence mask (a traitor is present but untrusted → presence ≠ trust).
- Apply `PHASE_C_REFINEMENTS.md`: (R1) EMA-smooth the inferred velocity (and add small sensing noise for
  realism), (R2) auxiliary regression loss + re-init the dead trust-slot weights to "wake" them, (R3)
  track FPR(<5%) / Time-to-Detect / detection-rate and plot trust(t) for one attacker.
- **Models (headline = M1 vs M2):** M0 = `comm8_lidar` (vulnerability ref); M1 = retrained vs rammers,
  NO explicit signal (baseline — does retraining alone teach evasion?); M2 = retrained vs rammers +
  threat signal (proposed defense). Both transfer from `comm8_lidar`.
- **CTDE guard:** threat score uses ONLY own-LiDAR; NEVER feed the ground-truth "is traitor" label into
  the policy (labels are for metrics only). Re-run the leakage test on M2.

## 5. The plan + the immediate next steps (full detail in PHASE_C_DEFENSE_PLAN.md)
1. STEP 1 (cheap, eval-only): `python probe_ram.py 1` and `python probe_ram.py 3` — how the drop scales.
2. STEP 2: train **M1** (retrain `comm8_lidar` vs rammers, curriculum 0→1→2 rammers, no explicit signal),
   eval vs f=2 rammers. KEY DECISION (likely fork — architecture is strong):
   - if M1 leaves a gap → build M2 (explicit threat signal).
   - **if M1 already recovers most of the 18pp** → matched success won't separate M1/M2; instead test
     **GENERALIZATION** (train on f=2, eval on unseen/harder: f=3-4, faster rammers, blocking, ram+lie,
     occlusion) — M2's edge usually shows there. If M1≈M2 even at hardest → reframe as
     "adversarial-curriculum yields emergent evasion" and drop the explicit mechanism (don't force it).
3. STEP 3: build **M2** (threat signal + refinements), eval, compare M1 vs M2 + detection metrics.
4. STEP 4: sweep f∈{1,2,3}; add ORCA baseline; (venue) multi-seed.

### Staged adversary schedule (order matters)
- **NOW:** ramming with **TRUE broadcasts** (`deception_mode="none"`, `traitor_behavior="ram"`) — isolate
  the physical threat + behavioral defense (STEP 1→3).
- **LATER (only after the above is done):** ramming + **FALSE signals** (ram+lie, set
  `deception_mode="false_velocity"` + `traitor_behavior="ram"`). Honest expectation: ram+lie ≈ ram at
  normal sensing (LiDAR overrides lies — proven), so it only bites under **occlusion/degraded LiDAR**.
  Pair the false-signal step with an occlusion/NLOS stress regime to make deception matter; otherwise
  it's a completeness check that the defense handles the combined attack.

### Why use communication at all? (reviewer-defense — be honest)
Our data shows comm is MODEST, so answer truthfully: (a) it **supplements LiDAR under occlusion/NLOS** —
its benefit grows with density (blackout cost 0.20→0.30 = −4.8pp→−7.9pp); (b) it's a measured ~5–8pp
coordination aid (neighbors-ablation: collisions ~4× at high density); (c) demonstrating **robustness to
its compromise** (deception/jamming inert) is itself a contribution that requires comm to be present.
Do NOT claim comm is "critical" (data contradicts it); claim **graceful, occlusion-relevant, attack-robust**.

## 6. Environment / run notes
- Run scripts with the env's python directly:
  `C:/Users/Srinivasa/miniconda3/envs/swarm_rl/python.exe <script>` (conda activate no-ops in
  non-interactive shells).
- Training: ~50 min per 5M-step run (10-worker multiprocessing, see `train_comm.py` pattern).
- Eval: single-process CPU, ~30–60 min per density-sweep; deterministic; **fixed counting** (use the
  `finished` set to avoid double-counting terminated agents); **paired seeds**
  `900_000_000 + int(density*100)*10_000 + map_idx + attempts*5_000`; 200 maps/density; densities {0.20,0.30}.
- Existing tooling to reuse/adapt: `train_comm.py`, `eval_comm.py`, `probe_ram.py`, `probe_deception.py`,
  `eval_ablate_feature.py`, `feature_sensitivity.py`, `test_no_leakage.py`.

## 7. Publishing reality (honest)
- Phase C (defense vs the real threat) done well = a publishable paper; Phase D not strictly required for
  a first publication. I cannot guarantee acceptance (venue + writing dependent).
- Traitor counts (from literature, n=10): Byzantine bound f<n/3 → sweep f∈{1,2,3} (headline f=2),
  optional f=4 breakdown.

## 8. Working-style notes (important)
- **Be honest and skeptical; don't inflate.** Earlier in this project, fabricated rejection-probability
  numbers and a few "the code doesn't have X" claims turned out wrong — VERIFY code by reading/running it
  before asserting. If I claim a feature is missing, check the actual file + run a quick end-to-end test
  (and watch for stale `__pycache__/*.pyc`).
- Prefer cheap probes before multi-week builds (that's how we avoided building a useless deception defense).
- Confirm the plan back to me before writing code.

FIRST TASK: read the files above, confirm you understand the pivot (deception inert, ramming is the
threat, build a behavioral defense), then help me execute STEP 1 → STEP 2 from PHASE_C_DEFENSE_PLAN.md.

# ===== END OF PROMPT =====
