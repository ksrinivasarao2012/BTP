# M0 Provenance & Transfer-Learning Lineage (paper-writing doc)

> **Created:** 2026-06-19 · **Purpose:** the complete, verified development history of the baseline
> navigator **M0** (`apex_ultra_glide_v14_comm8_lidar_final.zip`) — from the from-scratch model (v10) through
> six behavioural fine-tunes to M0, plus the Option-C noise fine-tune used by the temporal-trust paper.
> Written for the paper's *Methods / training-provenance* and the transfer-learning disclosure a reviewer
> will demand. **All facts below were read from the trainer files (paths in the table); nothing is guessed.**
>
> ⚠️ **Folder caveat:** the v10–v14 trainers live under `Phase B/Phase_B5_Synchronization/` but are the
> **B6→B10 `apex_ultra` family** — NOT the `train_step_B5_sync_*` family in the same folder (which produces a
> separate, unrelated `v10_Pro / v11_Trust / v12_Resilient` line). M0's ancestors are the `apex_ultra` chain
> only, confirmed by matching save/load filenames.

---

## 0. CTDE leak status (verify before trusting any of this)

M0 was leak-audited and declared **CTDE-clean** (`leak_test_local.py`): the actor's dependence on the
critic/global block is **0.0%**, the neighbour-stagnation leak is dead (**0.2%**). M0 **does** use
communicated neighbour position/velocity within 8 m (~18.7% influence) — this is a **modeled comm radio**,
disclosed as such (NOT a CTDE violation). See memory `CTDE_AUDIT_B10` / `dijkstra-goal-direction-crutch`.

**RE-VERIFIED 2026-06-19** (`leak_test_local.py models\apex_ultra_glide_v14_comm8_lidar_final.zip lidar`,
4000 obs):
| Ablation | Δ|action| rel. | reading |
|---|---|---|
| LIDAR | **174.8%** | test is sensitive (valid) ✅ |
| GLOBAL (critic block) | **0.0%** | actor ignores it → CTDE-clean ✅ |
| STAGNATION | **0.2%** | transfer leak dead ✅ |
| NEIGH_VEL | 18.7% | communicated neighbour velocity → **modeled 8 m comm radio (disclose)** |
| SYNC_RELVEL | 10.4% | communicated relative velocity → modeled comm (disclose) |
| CONGESTION | 11.6% | LiDAR-derived own-sensing feature (fine) |
→ **M0 is CTDE-clean.** The only inter-agent dependence is the disclosed 8 m comm radio (NEIGH_VEL +
SYNC_RELVEL ≈ 29%), not the global/critic state. The paper's CTDE claim stands.

---

## 1. The lineage at a glance

| Gen | Model file | Trainer (in `Phase B/Phase_B5_Synchronization/`) | Env | Parent | From scratch? |
|---|---|---|---|---|---|
| **v10** | `apex_ultra_queue_v10_final` | `train_step_B6_queue_v10.py` | `swarm_env_step_B6` | — fresh `PPO()` | ✅ **SCRATCH** |
| v11 | `apex_ultra_patience_v11_final` | `train_step_B7_patience_v11.py` | `swarm_env_step_B7` | v10 | fine-tune |
| v12 | `apex_ultra_positional_v12_final` | `train_step_B8_v12.py` | `swarm_env_step_B8` | v11 | fine-tune |
| v13 | `apex_ultra_topological_v13_final` | `train_step_B9_topological_v13.py` | `swarm_env_step_B9` | v12 | fine-tune |
| v14 | `apex_ultra_glide_v14_final` | `train_step_B10_extended_v14.py` | `swarm_env_step_B10` | v13 | fine-tune |
| **M0** | `apex_ultra_glide_v14_comm8_lidar_final` | `train_comm.py` (root) | `swarm_env_step_B10_8_0m` | v14 | fine-tune |
| (paper base) | `noise_robust_ON_stage{0,1}_final` | `Phase_CD/Noise_added/train_noise_robust.py` | `env_noisy_byzantine` | M0→collab→noise | fine-tune |

All hops keep the **same network** (`MAPPO_Extractor_B5`, 130-local actor / 520-global critic, 650-d obs) and
**warm-start** from the previous generation (`PPO.load`), changing only the **environment** (the new skill)
and lowering `learning_rate`/`ent_coef`. This is a **staged behavioural curriculum**, not six independent
models — the key fact to disclose.

---

## 2. Per-generation: problem → fix → why (the "and so on" you asked for)

### v10 — `queue` (SCRATCH baseline, env B6) — *"Smart Queuing & Directional Yielding"*
- **Problem:** with no learned etiquette, drones converging on the same gap/goal **collide or jam** at
  bottlenecks (the classic many-agent convergence pile-up).
- **Fix / change:** trained **from scratch** in the B6 env to learn **queuing and directional yielding** —
  who goes first through a gap, who waits.
- **Config:** `PPO(MAPPO_Policy_B5, ent_coef=0.03, lr=3e-4, n_steps=2048, batch_size=256)`; everything else
  SB3 defaults (`gamma=0.99, gae_lambda=0.95, clip_range=0.2, n_epochs=10, vf_coef=0.5, max_grad_norm=0.5`).
- **Why this first:** collision-free local interaction is the prerequisite for every later skill.

### v11 — `patience` (env B7) — *"Patience Decay + Deadlock Recovery"*
- **Problem:** v10's queuing **over-yields** → drones get **stuck forever in blocked queues** (deadlock):
  everyone politely waits and no one moves.
- **Fix:** fine-tune in B7 so the agent learns **patience decay** — after waiting too long, **break out** of
  a stalled queue (deadlock recovery).
- **Config:** `lr=1e-4`, `ent_coef=0.02`; curriculum **2M @ 0.30 → 5M @ 0.35** (7M steps).
- **Why:** turns a polite-but-frozen swarm into one that makes progress under congestion.

### v12 — `positional` (env B8) — *"Positional History Stagnation (Jitter Breaking)"*
- **Problem:** agents that aren't fully deadlocked still **jitter in place** / oscillate without net
  progress (local stagnation that isn't a hard deadlock).
- **Fix:** fine-tune in B8 using **positional history** to detect stagnation and **break the jitter** (commit
  to a direction instead of oscillating).
- **Config:** `lr=1e-4`, `ent_coef=0.02`; curriculum **2M @ 0.30 → 5M @ 0.35** (7M steps).
- **Why:** removes wasted-motion plateaus → cleaner trajectories, higher throughput.

### v13 — `topological` (env B9) — *"Topological Path Guidance"* ⚠️ (the Dijkstra heading enters here)
- **Problem:** locally-smooth motion can still follow a **globally poor route** (wandering, long detours).
- **Fix:** fine-tune in B9 with **topological / shortest-path guidance** — the agent is steered by a
  **global path heading**. **This is where the Dijkstra goal-direction heading (`obs[2:4]`) becomes
  load-bearing** (see `dijkstra-goal-direction-crutch`). It is a *privileged* signal → must be disclosed in
  the paper (Limitation 3 / §7).
- **Why:** large jump in path quality / success, *but* it is the crutch that caps the paper at MDPI and is
  the one RA-L blocker (P3). PhaseB2 (straight-line bearing) plateaus ~80% precisely because it lacks this.
  (Venue note: MDPI *Drones* superseded 2026-06-26 by the NO-APC constraint → current target Elsevier *RAS*;
  the point stands that the Dijkstra crutch, not the venue, is what caps the paper below top-tier robotics.)
- **Config:** `lr=1e-4`, `ent_coef=0.02`; curriculum **1M @ 0.30 → 2M @ 0.35** (3M steps).

### v14 — `glide` (env B10) — *"Adaptive Wall-Glide Fine-Tuning"*
- **Problem:** at **high obstacle density** the agent must follow obstacle/wall boundaries to find detours
  rather than stalling in front of them.
- **Fix:** fine-tune in B10 for **adaptive wall-gliding**; curriculum **density 0.30 (2M steps) → 0.35
  (3M steps)**, `lr=8e-5`, `ent_coef=0.015`, `VecNormalize(norm_reward=True, clip_reward=10.0)`.
- **Why:** mastery of dense detours → the ~92–95% no-adversary navigator.

### M0 — `comm8_lidar` (env B10_8_0m, `train_comm.py`) — *the communication baseline*
- **Change (not a "problem fix"):** fine-tune v14 with an **8 m gated communication radio** (neighbour
  pos/vel sharing) **+ LiDAR congestion**, **same 0.30→0.35 curriculum**, `lr=5e-5`, `ent_coef=0.015`.
  Produces the **CTDE-clean** M0 (net_arch 64×64; see §3).
- **Why:** M0 is the leak-audited, comm-enabled navigator on which the *paper's* contributions
  (collaborative perception → Byzantine attack → trust → temporal trust) are all built.
- **No-adversary success:** **95.6% (d=0.20) / 91.1% (d=0.30)**.

### Beyond M0 (the paper's actual base): collaborative-perception + Option-C noise fine-tune
- M0 → **`raster_slot_fusion_ON`** (collaborative obstacle-sharing, 3-stage 0.15→0.25→0.35) →
  **Option C** `train_noise_robust.py`: stage0 1.5M σ~U[0,0.3] @ density 0.20; stage1 2.0M σ~U[0,0.6] @
  density 0.25; `lr=3e-5`, `ent_coef=0.020`. Output `noise_robust_ON_stage1_final` = the model evaluated in
  §5.7–5.11 and the adaptive-attacker sweeps.

---

## 3. Base PPO hyperparameters (set at v10 scratch, carried through every fine-tune)

**VERIFIED 2026-06-19 by reading the checkpoints directly (`dump_hparams.py`) — authoritative:**

| Param | M0 (`...comm8_lidar`) | `noise_robust_ON_stage1` (paper base) | Source |
|---|---|---|---|
| policy / **net_arch** | MAPPO_Policy_B5, **pi=[64,64], vf=[64,64]** | same | checkpoint |
| obs | 650-d (130 local actor / 520 global critic) | same | checkpoint |
| learning_rate | **5e-5** (comm stage; v14 was 8e-5, v10 3e-4) | **3e-5** (Option C) | checkpoint |
| ent_coef | **0.015** | **0.02** | checkpoint |
| n_steps | 2048 | 2048 | v10 `PPO()` |
| batch_size | 256 | 256 | v10 `PPO()` |
| gamma | 0.99 | 0.99 | SB3 default (kept) |
| gae_lambda | 0.95 | 0.95 | SB3 default |
| clip_range | 0.2 | 0.2 | SB3 default |
| n_epochs | 10 | 10 | SB3 default |
| vf_coef / max_grad_norm | 0.5 / 0.5 | 0.5 / 0.5 | SB3 default |
| n_envs (rollout) | 100 | 100 | checkpoint |
| VecNormalize | `norm_obs=False, norm_reward=True, clip_reward=10.0` | same | trainer |

> ✅ **LOCKED.** ⚠️ Two corrections vs the trainer-lineage guess: (1) **net_arch is 64×64**, NOT [256,128]
> (that was the unrelated v15 line); (2) **M0's final lr = 5e-5** (the comm stage lowered it from v14's
> 8e-5). The base (gamma/n_steps/batch/gae_lambda/clip/n_epochs) is identical across M0 and the noise base —
> only lr/ent_coef differ.

---

## 4. What to write in the paper (transfer-learning disclosure)

One honest paragraph, e.g.:
> *"The navigator was developed through a staged behavioural curriculum: a base policy trained from scratch
> for collision-free queuing (v10) was successively fine-tuned — adding deadlock recovery (v11),
> anti-stagnation (v12), global path guidance (v13), and high-density wall-gliding (v14) — each generation
> warm-started from the previous in an environment that introduced the new skill, with no change to the
> network architecture. The final navigator (M0) adds an 8 m gated communication radio. We report M0's
> configuration and acknowledge it inherits a global shortest-path heading (introduced at the path-guidance
> stage) as a privileged input (§7)."*

**Per-stage curriculum (all verified from the trainers):**
| Gen | lr | ent_coef | curriculum (steps @ density) |
|---|---|---|---|
| v10 (scratch) | 3e-4 | 0.03 | trained in B6 (queuing) |
| v11 | 1e-4 | 0.02 | 2M @ 0.30 → 5M @ 0.35 |
| v12 | 1e-4 | 0.02 | 2M @ 0.30 → 5M @ 0.35 |
| v13 | 1e-4 | 0.02 | 1M @ 0.30 → 2M @ 0.35 |
| v14 | 8e-5 | 0.015 | 2M @ 0.30 → 3M @ 0.35 |
| M0 (comm) | 5e-5 | 0.015 | 0.30 → 0.35 (same as v14) |
| Option-C s0/s1 | 3e-5 | 0.020 | 1.5M σ~U[0,0.3]@0.20 → 2.0M σ~U[0,0.6]@0.25 |

(Only v10's exact total step count isn't pinned here — it's the from-scratch B6 run; all fine-tune
step counts above are verified.)

---
*Companion to `PARAMETER_JUSTIFICATION_PHASE_CD.md` (params + gaps), `PARAMETER_JUSTIFICATION.md` (physical,
cited), `FINAL_PARAMETER.md` (density). This file = the M0 build history + base hyperparameters.*
