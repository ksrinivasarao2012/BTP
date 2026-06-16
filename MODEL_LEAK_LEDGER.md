# Model Leakage Ledger + Results Audit

**Date:** 2026-06-16 · **Evidence:** `leak_test_local.py`, training-script reads, `CTDE_LEAKAGE_INVESTIGATION.md`
**Purpose:** classify every model as LEAKY vs CLEAN, then audit which `.md`/result claims came from leaky
models and state exactly what must change for a clean sheet.

## Definitions (what counts as a leak)

A **leak** = the *actor* (the deployed drone brain) is fed information a real decentralized drone could not
obtain. Two leak channels in this codebase:
- **Omniscient neighbors** — neighbor positions/velocities of ALL drones with **no range gate**
  (`swarm_env_step_B10.py` and earlier). Severe.
- **Ground-truth congestion** — `congestion_mode="env"`: an exact count of drones within 1 m, not sensed.
  Mild (measured ~4.6 % action dependence) but still privileged.

NOT leaks (verified): the **critic/global block** `obs[130:650]` (never in the actor's forward pass → 0.0 %);
neighbor **stagnation** counters (actor ignores them, ~0.2 %); **gated** neighbor comm within a finite range
(a *modeled radio* — must be disclosed, but realistic); **LiDAR-based** congestion (own sensor).

---

## TABLE A — LEAKY models (do NOT use for the clean headline)

| Model file | Trained by / env | Comm gating | Congestion | Leak type | Severity | Verified |
|---|---|---|---|---|---|---|
| `apex_ultra_queue_v10_*` | B6 queue / old env | **ungated** | env | omniscient + GT congestion | severe | inferred (pre-gating) |
| `apex_ultra_patience_v11_*` | B7 / old env | **ungated** | env | omniscient + GT congestion | severe | inferred |
| `apex_ultra_positional_v12_*` | B8 / old env | **ungated** | env | omniscient + GT congestion | severe | inferred |
| `apex_ultra_topological_v13_*` | B9 / old env | **ungated** | env | omniscient + GT congestion | severe | inferred |
| `apex_ultra_glide_v14_*` (mid/final) | `swarm_env_step_B10.py` | **ungated** | env | omniscient + GT congestion | severe | **code-verified** |
| `v15_Master_*` … `v20_*` | B5_v15–v20 master envs | **ungated** (pre-gating) | env | omniscient + GT congestion | severe | inferred (not audited) |
| `apex_ultra_glide_v14_comm3_final` | `train_comm.py 3` | 3 m (ok) | **env** | GT congestion | mild | config-verified |
| `apex_ultra_glide_v14_comm5_final` | `train_comm.py 5` | 5 m (ok) | **env** | GT congestion | mild | config-verified |
| `apex_ultra_glide_v14_comm0_final` | `train_comm.py 0` | none (ok) | **env** | GT congestion | mild | config-verified |
| `apex_ultra_glide_v14_8_0m_final` | `train_step_B10_extended_v14_8_0m.py` | 8 m (ok) | **env** | GT congestion | mild | **leak-test-verified (4.6 %)** |

## TABLE B — CLEAN models (safe for publication)

| Model file | Trained by | Comm gating | Congestion | Status | Verified |
|---|---|---|---|---|---|
| `apex_ultra_glide_v14_comm8_lidar_final` **(M0 — headline)** | `train_comm.py 8 lidar` | 8 m | **lidar** | actor uses only LiDAR + 8 m radio; global 0.0 %, stagnation 0.2 %, congestion from own LiDAR | **leak-test-verified** |
| `apex_ultra_glide_v14_comm0_nocong_final` | `train_comm.py 0 nocong` | none | **off** | cleanest possible (LiDAR + ego only) but NO comm → can't show "comm matters" | config-verified |
| `apex_ultra_glide_M1_ram_final` (M1) | `train_ram_M1.py` (transfer from M0) | 8 m | **lidar** | same clean config as M0 | config-verified |

**Bottom line:** the only clean model that *also* has a working comm channel (needed for the paper's comm
story) is **M0 = `apex_ultra_glide_v14_comm8_lidar_final`**. That is the headline model. `comm0_nocong` is
clean but commless; `M1` is clean (the ram-trained variant).

---

## RESULTS AUDIT — which claims came from leaky models, and the fix

| Result / claim | Script (default model) | Model used | Clean? | Action required |
|---|---|---|---|---|
| **Phase B headline 95.55/91.10** | probe BASELINE = comm8_lidar | M0 | ✅ clean | none |
| **Ram scaling f=1/2/3** (−9pp/rammer) | `probe_ram.py` (comm8_lidar) | M0 | ✅ clean | none |
| **Deception inert** | `probe_deception.py` (comm8_lidar) | M0 | ✅ clean | none (reword "robust despite influence") |
| **Oracle ceiling ~75-80 %** | `probe_ram_oracle*.py` (comm8_lidar) | M0 | ✅ clean | none |
| **Comm RANGE sweep (3/5/8/∞ flat)** | `eval_comm.py` (comm3,comm5,v14_8_0m,v14_final) | comm3/5 + v14_8_0m + **v14_final (omniscient)** | ❌ **leaky + confounded** | **RE-RUN** sweep with `congestion=lidar` at every range; drop `v14_final` (∞) or replace with a gated-large-range clean model |
| **Comm BLACKOUT (−5-8pp)** | `eval_comm_blackout.py` (**v14_8_0m**) | v14_8_0m | ❌ leaky (GT congestion) | **RE-RUN** on `comm8_lidar` |
| **Congestion ablation** | `eval_nocongestion.py` (**v14_8_0m**) | v14_8_0m | ❌ leaky | superseded — use the clean `leak_test_local.py` congestion result (M0 = 11.6 %, LiDAR-based) or re-run on `comm8_lidar` |
| **Feature-importance ablation** | `eval_ablate_feature.py` (**v14_8_0m**) | v14_8_0m | ❌ leaky | **RE-RUN** on `comm8_lidar` |
| **Feature sensitivity (LiDAR≫comm)** | `feature_sensitivity.py` (**v14_8_0m/v14_final**) | leaky | ❌ leaky | **RE-RUN** on `comm8_lidar` |

**Severity note:** every "❌" result is contaminated only by the *mild* ground-truth-congestion leak (or, for
the ∞ point, the severe omniscient leak). The qualitative conclusions (comm range barely matters; LiDAR
dominates; comm fields minor) are **likely to survive** re-running on the clean model — in fact the clean M0
leans *more* on its own-LiDAR congestion (11.6 % vs 4.6 %), which *strengthens* the "LiDAR-grounded" story.
But for a clean sheet they must be **re-run and re-cited on `comm8_lidar`**, not asserted.

---

## CLEAN-SHEET ACTION CHECKLIST

1. **Headline = `apex_ultra_glide_v14_comm8_lidar_final` (M0)** everywhere. Retire `v14_8_0m`, `v14_final`,
   `comm3/5/0`, `v15-v20` to "early/leaky variants — not used for reported results."
2. **Re-run on M0** (change each script's `MODEL_PATH`/default to `comm8_lidar` and `congestion=lidar`):
   `eval_comm_blackout.py`, `eval_ablate_feature.py`, `feature_sensitivity.py`, and the `eval_comm.py` range
   sweep (lidar congestion at all ranges).
3. **Disclose the 8 m comm model** in the paper (one paragraph; draft in `CTDE_LEAKAGE_INVESTIGATION.md` §6).
4. **Add the comm-degradation robustness eval** (noise/dropout) to pre-empt "are you sure".
5. **Reword** the deception claim → "robust outcome despite comm influence" (comm is used ~19 %, not ignored).
6. **Ship as supplementary:** `leak_test_local.py`, `CTDE_LEAKAGE_INVESTIGATION.md`, this ledger.
7. **Update docs** `PATH_B_ANALYSIS_PAPER.md` / `PHASE_CD_PATHS_A_AND_B.md`: mark the comm-analysis results as
   "to be re-run on M0" until the re-runs land.

## Still-unverified (be honest in the paper)
- `v15_Master_*`–`v20_*` env comm-gating was **not** audited (assumed ungated, pre-gating). They are not used
  for reported results, so this doesn't affect the clean sheet — just don't cite them.
