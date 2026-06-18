# START HERE — Context Handoff (slot-fusion comm-value work)

**For:** a fresh Claude/Opus chat picking up this work.
**Date:** 2026-06-18 · **Owner:** Srinivasa (address him as "Srinivasa," and NEVER run commands
automatically — always show the command and wait for his "run it").

> ⚠ First instruction to the new chat: **do not trust this summary blindly — verify against the actual
> files before acting.** Read these three first: `swarm_env_raster.py` (the env),
> `eval_slot_fusion_zero_shot.py` (the eval), and `SLOT_FUSION_CORRECT_FIX.md` (the pending fix).
> Everything below is a map, not the territory.

---

## 1. The goal (one paragraph)
Project TA-MAPPO: 10-drone swarm navigates to a shared goal with LiDAR + inter-drone communication, for an
IEEE RA-L paper. The current question: **is communication load-bearing?** i.e., when drones lose their own
LiDAR (sensor failure), does sharing obstacle info with neighbors meaningfully improve success? After that
is proven, the paper's headline is a **trust mechanism** that defends against **traitor** drones that
broadcast false obstacles (Phase 4, not started).

## 2. How we got here (the short story)
- **Separate-channel design failed.** The shared obstacle map sat in its own slot `obs[130:178]` (698-d
  obs). Feature-importance showed the policy **ignored it** (~0 drop). A flat MLP over concatenated inputs
  never learned to read that channel.
- **The info was fine, the slot was wrong.** `probe_raster.py` routed the shared map into the LiDAR slot
  `obs[6:54]` (the slot the policy already reads) and M0 navigated **~85–90% zero-shot**. So the
  information is sufficient; the network just never read the separate channel.
- **Gate 0 ruled out the other suspect.** Removing the privileged global-Dijkstra heading at `obs[2:4]`
  did NOT raise the shared map's importance → the Dijkstra "crutch" was not the blocker.
- **Pivot → slot-fusion.** Fuse the shared map INTO `obs[6:54]` (one obstacle channel, 650-d), **reusing
  M0's existing 130-d actor weights — no new architecture, no surgery, no from-scratch training.**

## 3. The current result (from Srinivasa's runs — regenerate to confirm)
`eval_slot_fusion_zero_shot.py`, regime dropout=0.10/sustain=5 (≈33% blind), zero-shot on M0:
- **ON 93.55% / OFF 54.70% / +38.85 pp.** Statistically overwhelming. Communication clearly helps.
- **Two caveats:** (a) it's a **same-weights ablation** (both arms use M0), not trained-vs-trained — the
  fair paper number needs a *trained* comm-OFF baseline; (b) a **known bug** inflated ego vision to 12 m
  (see §4), so this exact number must be re-run after the fix.

## 4. THE PENDING FIX (do this first) — ego range 8 m vs 12 m
**Bug (verified in `swarm_env_raster.py`):** in `_fused_lidar` the ego's own-obstacle branch (~lines
106–109) appends **all** obstacles unfiltered, and `_cast48` ranges to `collab_range = 12 m`. So a
**sighted drone sees 12 m, not the intended 8 m.** The neighbor branch is correctly filtered to 8 m.
The OFF path in `_observe` (~lines 215–218) has the same unfiltered-ego bug.

**Correct fix (in `SLOT_FUSION_CORRECT_FIX.md` §3):** filter the ego's obstacles to `<= self.lidar_range`
(8 m), but **keep the cast and `/collab_range` normalization at 12 m.**
**Do NOT "cast at 8 m"** — M0 was trained on the 12 m scale; changing the cast/normalization to 8 m puts
obstacles out of distribution and M0 collapses. Range = which obstacles enter the list, NOT the cast
distance. After the fix, re-run the §3 eval and report new ON/OFF/gap. Expect both to drop a bit; the gap
should stay large (maybe widen).

## 5. Leak-safety invariants (publication-critical — never violate)
- Actor reads `obs[:130]` only. Critic reads `obs[130:]`. Never let actor code touch the global block.
- Shared/neighbor info is **sender-gated** (a blind neighbor shares nothing) AND within
  `communication_range` (10 m). Never read the global obstacle list as the ego's own knowledge.
- Keep cast + normalization at `collab_range` (12 m) so M0 stays in-distribution.
- **Never set `collab_comm=True`** — that's the OLD leaky collaborative-sensing mode (CTDE leak).
- Apply any sensing change to BOTH ON and OFF arms so the comparison stays fair.

## 6. Key constants (verified in code)
- `collab_range = 12.0` (M0's native LiDAR scale; `swarm_env_phasecd.py:48`).
- M0 trained at LiDAR **12 m**; test regime uses `lidar_range = 8.0` (creates an 8–10 m comm-only annulus).
- `communication_range = 10.0`. Obs: 698-d (separate-channel legacy) or **650-d** (slot-fusion / probe).
- Actor 130-d local + critic 520-d global.

## 7. Script paths — use the RIGHT ones (common trap)
| Purpose | USE | Do NOT use (incompatible 698-d/178-d) |
|---|---|---|
| Slot-fusion ON/OFF eval | `eval_slot_fusion_zero_shot.py` (650-d, 130-d actor, `slot_fusion=True`) | `eval_raster.py` |
| "Did it use comm?" per stage | ON vs OFF eval at that dropout (toggle `use_shared_map`) | `feature_importance_raster.py` (ablates `[130:178]`, gone in slot-fusion) |
| Training | a new `train_slot_fusion.py` built on `MultiProcessRasterEnv` from `train_raster.py` (PettingZoo 10-agent), `slot_fusion=True`, stage-chained | plain `SubprocVecEnv([env])` — can't wrap the multi-agent env |

Model: load `models/apex_ultra_glide_v14_comm8_lidar_final.zip` (= **M0**). Save fine-tunes as
`models/raster_slot_fusion_{ON,OFF}_stage{N}_final.zip`.

## 8. Next steps (after the §4 fix + re-run)
**Gate 2 — light fine-tune (not from scratch):**
1. Train comm-ON, 3 short stages, dropout 0.10 → 0.15 → 0.20, chained (each stage loads the previous).
   Check comm value (ON vs OFF eval) after each stage.
2. Train comm-OFF the same way → the fair baseline.
3. **Hardened eval:** n ≥ 500 maps, seed the dropout RNG for true ON/OFF pairing, report ON−OFF with a
   bootstrap 95% CI. Pass if CI lower bound > 0 and gap is large.
**Then Phase 4:** add traitor drones + the trust-weighted fusion (the paper's headline).

## 9. Docs already written this session (read for detail, treat as drafts to verify)
- `SLOT_FUSION_CORRECT_FIX.md` — the pending ego-range fix + re-run (most current; start here after this).
- `GATE_1_RESULT_AND_GATE_2_PLAN.md` — Gate 2 plan. NOTE its "Fix 0 = cast at 8 m" is WRONG (see §4 above);
  its per-stage FI gates and `eval_raster.py` usage are also wrong (see §7). Use it for structure only.
- `IMPL_SPEC_FOR_HANDOFF.md`, `ARCHITECTURE_FIX_PLAN.md` — earlier reasoning; partly superseded by the
  slot-fusion pivot. Cross-check against the code before relying on any specific instruction.

## 10. Environment / run rules
- Python (full path): `C:\Users\Srinivasa\miniconda3\envs\swarm_rl\python.exe`; conda env `swarm_rl`.
- Repo root: `D:\Swarm\BTP`; this work lives in `Phase_CD\Collab_Perception\`.
- Show commands first; never auto-run. Address Srinivasa by name.

---
**TL;DR for the new chat:** Read `swarm_env_raster.py` + `eval_slot_fusion_zero_shot.py` + this file. The
big result (+38.85 pp, comm helps) is real but needs (1) the ego-range fix in §4, (2) a re-run, (3) a
trained OFF baseline for the fair number. Don't use `eval_raster.py`/`feature_importance_raster.py` on
slot-fusion models. Verify before you act.
