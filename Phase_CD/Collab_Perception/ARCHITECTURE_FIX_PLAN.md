# Architecture-Fix Plan — Making the Shared Map Load-Bearing

**Owner:** Srinivasa
**Created:** 2026-06-18
**Scope:** Phase_CD / Collab_Perception (raster architecture)
**Status:** Gate 0 DONE → pivoted to slot-fusion. Next: zero-shot ON/OFF eval (after the §3.2 scale fix).

> **Working rule (non-negotiable):** No command in this document is run automatically.
> Every command below is to be **shown and approved by Srinivasa first**. The ▶ marker = "proposed
> command, do not run until approved." The ⏸ marker = "STOP and bring results to Srinivasa for review."

> ### UPDATE 2026-06-18 — Gate 0 result + pivot to slot-fusion
> **Gate 0 (remove Dijkstra heading): NEGATIVE.** SHARED_MAP feature-importance drop stayed ≈0/negative
> with *and* without the Dijkstra heading (−6.0 → −4.7 pp at d=0.20). So the Dijkstra crutch is **not**
> the blocker. Cross-referenced with `probe_raster.py` (~85–90% zero-shot when the shared map is in the
> **LiDAR slot `[6:54]`**) vs feature importance (~0 when it's in the **separate `[130:178]` slot**), the
> real diagnosis is: **information is sufficient; the policy never reads the separate channel.**
> **Pivot:** abandon the separate-channel raster design; fuse the shared map into `[6:54]` (the slot M0
> already uses). This **reuses M0's existing weights — no new architecture, no surgery, no from-scratch
> training.** Implemented as `slot_fusion=True` in `swarm_env_raster.py` + `eval_slot_fusion_zero_shot.py`.
> **One required fix first:** a normalization scale mismatch (own/8 m vs shared/12 m) that would confound
> ON−OFF — see `IMPL_SPEC_FOR_HANDOFF.md` §3.2. Phases 1–4 below still apply; "Phase 1 fusion" now means
> slot-fusion into `[6:54]`, not the `[130:178]` channel.

---

## 0. Why this document exists

The current blind-force curriculum is trying to *discover* a dependence on the shared obstacle map
(`obs[130:178]`) by brute force. A code-level audit (2026-06-18) shows the design is **structurally
biased against** that dependence, so the gate (`comm_value = ON − OFF ≥ 5 pp`) is likely to land on
the noise floor even if every stage runs perfectly. This plan replaces "hope the MLP learns it" with
"make the shared map load-bearing by construction," and lays out a cheap probe to confirm the
direction **before** spending the big compute.

---

## 1. Findings (evidence, not opinion)

### F1 — The Dijkstra goal-direction crutch is still in the observation
- `swarm_env_phasecd.py:471` → `to_goal = self.get_shortest_path_direction(pos)`; `:496` places it at `obs[2:4]`.
- `get_shortest_path_direction` reads `self.shortest_path_map`, a **global Dijkstra map built from all
  obstacles at reset** (`:300`; solver `:114–160`).
- `swarm_env_raster.py:21,29,142` inherits this unchanged.
- **Effect:** every drone — ON or OFF, blind or sighted — is told the optimal obstacle-avoiding heading
  for free. Global routing (the hard part) is solved privately, so LiDAR / shared-map only matter for
  the last few cm. This is *why* `CLAUDE.md` says "communication is inert."

### F2 — The actor is a flat early-concat MLP; the shared map is a near-duplicate of own-LiDAR
- Actor = `nn.Linear(178, …)` over the whole local vector (`train_raster.py:87–90,:97`).
- Shared map `obs[130:178]` and own-LiDAR `obs[6:54]` are produced by the **same** `_cast48` routine in
  the **same** 16-sector {min,mean,std} format (`swarm_env_raster.py:92`).
- When sighted (majority regime in S1–S3) the two blocks are highly correlated and own-LiDAR is always
  reliable → PPO leans on own-LiDAR, treats the shared map as redundant.
- **Evidence it already happened:** after a *maximal* intervention (60% permanent blindness, Stage 0),
  SHARED_MAP feature-importance only reached **6 pp**, behind 18–20 pp features. ~6 pp is roughly the
  ceiling this design allows; the Stage-3 target is ≥10 pp.

### F3 — No reliability gate
- When a drone goes blind the env freezes its LiDAR block to constants (`swarm_env_raster.py:151–152`)
  but gives the actor **no "LiDAR is dead" signal**. One static set of weights must serve both sighted
  and blind states. A single linear layer cannot cleanly switch "ignore A, use B"; it learns a blurry
  compromise. "Use B when A fails" is the worst case for a flat concat-MLP.

### F4 — Zero-init + low LR + decaying blindness can erode the dependency
- The 48 shared-map columns start at exactly zero (`surgical_expand_raster.py:107,116`).
- Fine-tune LR is `3e-5` for all stages (`train_raster.py:289`); Stages 1–3 hand LiDAR back, so the
  gradient re-anchoring on own-LiDAR competes with *maintaining* shared-map weights.
- **Prediction (not yet data):** SHARED_MAP FI may slide between S1 and S3. If it drifts 6 → <5, the
  gate fails for this reason.

### F5 — The comm-OFF baseline is a strawman
- In OFF, a blind drone has own-LiDAR masked **and** shared map zeroed (`swarm_env_raster.py:150–153`)
  → ~6/10 drones fly with zero obstacle info. ON − OFF then measures "blind drones crash," not
  "communication is valuable." Reviewers will reject this.

### F6 — The gate is statistically marginal
- At p≈0.75, n=200: SE(p)=3.06 pp; SE(Δ) for two runs ≈ 4.3 pp. A 5 pp gate ≈ 1.15 σ (p≈0.25) — not
  significant. `eval_raster.py:84` seeds maps identically for ON/OFF (partial pairing, good), but the
  dropout pattern uses unseeded global `np.random` (`swarm_env_raster.py:65`), eroding the pairing.
- Minor bugs: `eval_raster.py:30` hardcodes `DROPOUT_SUSTAIN=20` while Stage 3 trains at `sustain=25`
  (train/eval mismatch); `train_raster.py:19` docstring still describes the *old* Stage-1 values (the
  `CURRICULUM` array `:77` is correct).

### Root cause (one sentence)
Navigation is solved privately by the Dijkstra heading **and** the shared map is an architecturally
redundant duplicate of own-LiDAR with no reliability gate — so brute-force blindness can only ever
nudge the channel to a weak, possibly non-durable ~6 pp.

---

## 2. The fix in one line

Stop trying to *discover* the dependency; **engineer** it. (1) Confirm the lever with a 1-day probe,
then (2) fuse own-LiDAR and the shared map into a single reliability-gated obstacle channel so the
shared map is load-bearing by construction, then (3) retrain and evaluate honestly.

---

## 3. Phased plan with review checkpoints

Legend: ▶ proposed command (do not run until approved) · ⏸ STOP, bring to Srinivasa · ✅ pass criterion.

### Phase 0 — Decisive feasibility probe (≈1 day, cheap)
**Goal:** prove that removing the Dijkstra crutch actually makes the shared map matter, before any
big training. This decides *which paper we are writing* (comm-matters vs. fundamental-limit).

Steps:
1. Add a probe switch to the env: replace `obs[2:4]` with a **straight-line bearing** `(goal−pos)/‖·‖`
   (no obstacle knowledge), leaving everything else identical. New flag, e.g. `straight_line_goal=True`.
2. Re-measure SHARED_MAP feature-importance and comm-blackout on the existing Stage-0 model under the
   straight-line heading (zero-shot first, then a short 500k finetune if needed).

▶ (after I write the env flag — shown for approval first)
```
$py = "C:\Users\Srinivasa\miniconda3\envs\swarm_rl\python.exe"
cd "D:\Swarm\BTP"
& $py Phase_CD\Collab_Perception\feature_importance_raster.py models\raster_blind_ON_stage0_final.zip 12 10 0.60 on 30 --straight-line
```

⏸ **REVIEW GATE 0 — bring me:** SHARED_MAP drop with vs. without the Dijkstra heading.
- ✅ If the drop **jumps well above 6 pp** when the crutch is removed → the lever is real → proceed to
  Phase 1.
- ⚠ If it **barely moves** → the channel is fundamentally redundant; we pivot to
  `backup/OPTION_1_LIMIT_PAPER.md` (fundamental-limit paper) instead of burning compute.

### Phase 1 — Implement the fused, reliability-gated obstacle channel (Option A)
**Goal:** make the shared map non-redundant by construction.

Design (Option A, input-level fusion):
- Replace the two separate 48-d blocks (own-LiDAR `[6:54]`, shared-map `[130:178]`) with **one 48-d
  "best obstacle estimate"** = sector-wise `min` over {own-LiDAR when sighted, shared-map}, **plus** a
  16-d "this sector is comm-only" provenance flag.
- comm-OFF becomes literally own-LiDAR-only; comm-ON adds the annulus + blind coverage → the shared
  map *is* the obstacle channel whenever the ego is blind.
- Touches: `swarm_env_raster.py._observe` (build fused channel), actor input width, and the surgery
  script. I will write these and **show the diff first**.

⏸ **REVIEW GATE 1 — bring me:** the proposed diffs for `_observe`, the actor extractor, and the
surgery, plus an env self-test (obs shape + a sanity check that OFF==own-LiDAR-only). Approve before training.

> Optional upgrade **Option B (learned gate)** — `g = σ(MLP([own_sector, shared_sector, blind_flag]))`.
> This gate later *becomes* the B4 T-Cell trust module. Decide A-only vs. A→B at Review Gate 1.

### Phase 2 — Retrain the curriculum on the fused architecture
- Re-run surgery for the new input layout, then the 4-stage curriculum for **comm-ON**.
- Keep Stage-0 blind-force (it's a good idea), but add a **blind-flag input** and consider a higher LR
  on the fused-channel columns so the dependency forms and *holds*.

▶ (after Phase 1 approved)
```
$py = "C:\Users\Srinivasa\miniconda3\envs\swarm_rl\python.exe"
cd "D:\Swarm\BTP"
& $py Phase_CD\Collab_Perception\surgical_expand_raster.py models\apex_ultra_glide_v14_comm8_lidar_final.zip models\raster_fused_M0.zip
& $py Phase_CD\Collab_Perception\train_raster.py 10 on 0
```
⏸ **REVIEW GATE 2a — after Stage 0:** SHARED_MAP / fused-channel FI must be ✅ ≥ 5 pp. Bring me the number.

▶ (only after Gate 2a passes — one stage at a time, FI between each)
```
& $py Phase_CD\Collab_Perception\train_raster.py 10 on 1
& $py Phase_CD\Collab_Perception\feature_importance_raster.py models\raster_blind_ON_stage1_final.zip 10 10 0.10 on 30
```
⏸ **REVIEW GATE 2b — after Stage 1:** FI must still be ✅ ≥ 5 pp (watch for the F4 erosion). Bring me the number.

▶ (after 2b)
```
& $py Phase_CD\Collab_Perception\train_raster.py 10 on 2
& $py Phase_CD\Collab_Perception\eval_raster.py models\raster_blind_ON_stage2_final.zip 8 10 0.20 on 30
& $py Phase_CD\Collab_Perception\train_raster.py 10 on 3
```
⏸ **REVIEW GATE 2c — after Stage 3:** FI ✅ ≥ 10 pp. Bring me the number before eval.

### Phase 3 — Honest baseline + hardened gate eval
**Goal:** make ON − OFF mean "comm vs. best non-comm coping," measured with real statistics.

Fixes to apply (I will show diffs first):
1. **Honest OFF fallback:** when blind, OFF uses last-known obstacle map / speed-reduction instead of
   zeros. (Replaces the F5 strawman.)
2. **Seed the dropout RNG** (`swarm_env_raster.py:65`) so ON/OFF see identical blind patterns → true pairing.
3. **Match eval sustain to train** (`eval_raster.py:30` → 25).
4. **n ≥ 500 paired maps**, report ON − OFF with a **bootstrap 95% CI**, not a bare 5 pp line.

▶ (after Phase 2 + diffs approved)
```
& $py Phase_CD\Collab_Perception\train_raster.py 10 off 0   # then 1,2,3 with FI between, same as ON
& $py Phase_CD\Collab_Perception\eval_raster.py models\raster_blind_ON_final.zip  8 10 0.20 on  500
& $py Phase_CD\Collab_Perception\eval_raster.py models\raster_blind_OFF_final.zip 8 10 0.20 off 500
```
⏸ **REVIEW GATE 3 — the real gate.** Bring me ON, OFF, and the **CI on the difference**.
- ✅ `comm_value = ON − OFF` with its 95% CI **lower bound > 0** (ideally point estimate ≥ 10 pp) → proceed to B4.
- ❌ otherwise → reassess (extend training, strengthen fusion, or fall back to OPTION_1).

### Phase 4 — Trust module + traitor attack (B4)
Only after Gate 3 passes. If we built Option B, the learned gate **is** the T-Cell trust mechanism —
introduce traitor drones that broadcast false obstacles and show the gate down-weights them. This is
the paper's headline contribution.

⏸ **REVIEW GATE 4:** design of the traitor attack + trust-gate eval, before running.

---

## 4. Quick decision table

| Checkpoint | Pass criterion | If fail |
|------------|----------------|---------|
| Gate 0 (probe) | SHARED_MAP drop ≫ 6 pp without Dijkstra heading | Pivot to OPTION_1 limit paper |
| Gate 1 (design) | Diffs sane, OFF==own-LiDAR-only verified | Iterate on fusion design |
| Gate 2a (S0) | FI ≥ 5 pp | Increase blind-force / LR on fused cols |
| Gate 2b (S1) | FI ≥ 5 pp (no erosion) | Raise fused-col LR, add blind-flag |
| Gate 2c (S3) | FI ≥ 10 pp | Extend training / strengthen gate |
| Gate 3 (eval) | 95% CI of ON−OFF lower bound > 0 | Reassess vs. OPTION_1 |
| Gate 4 (trust) | Gate down-weights traitors | Tune trust module |

---

## 5. What I need from you now

Pick the starting point at **Review Gate 0 setup**:
- **A) Approve Phase 0** — I write the straight-line-bearing env flag, show you the diff, and (on your
  go) we run the probe. *Recommended — cheapest path to certainty.*
- **B) Skip the probe, go straight to Phase 1 fusion** — faster to the new architecture but spends
  build effort before confirming the lever.
- **C) Adjust the plan** — tell me what to change.

Nothing gets written or run until you say so.
