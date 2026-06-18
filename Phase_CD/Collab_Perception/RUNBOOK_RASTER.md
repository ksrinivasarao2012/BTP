# Runbook — Raster shared-map architecture (Lever 2)

Step-by-step execution for the rasterized shared-obstacle-map design under LiDAR dropout.
Architecture/rationale: `DESIGN_RASTER_TRUST.md`. **You run; paste numbers; stop at ⛔ checkpoints.**

```powershell
$py = "C:\Users\Srinivasa\miniconda3\envs\swarm_rl\python.exe"
# clear stale bytecode if needed:
Get-ChildItem -Recurse -Directory __pycache__ | Remove-Item -Recurse -Force
```

## Why this design (one paragraph)
Sharing individual obstacles scales badly (nearest-per-neighbor blind = 50%; even k=5 = 81% at 135 dims).
Sharing a **rasterized map** of neighbor obstacles is fixed-size and works (`full_blind` = 88/90). So: a
separate **48-d shared-obstacle map** channel (16 sectors × {min,mean,std}) at `obs[130:178]`, distinct from
the own LiDAR `[6:54]` so it survives dropout. Trust lives in the **fusion** (down-weight liars before
rasterizing), not the obs. Actor obs = **130 local + 48 shared-map + 520 global = 698**.

## Files
| file | role |
|---|---|
| `swarm_env_raster.py` | env: 48-d shared-map channel + per-step sustained LiDAR dropout + **sender-gating** (blind drone shares nothing) |
| `probe_raster.py` | B1 validation (shared-map via lidar slot, zero-shot M0) |
| `surgical_expand_raster.py` | B2 surgery: actor input 130→178, zero-init |
| `train_raster.py` | B3 trainer (comm-ON / comm-OFF under dropout) |
| `eval_raster.py` | B3 gate eval (no adversary, under dropout) |

---

## B1 — Env validation ✅ DONE
```powershell
& $py Phase_CD\Collab_Perception\probe_raster.py models\apex_ultra_glide_v14_comm8_lidar_final.zip 30
```
| check | result | verdict |
|---|---|---|
| obs dim (normal) | **698** | ✅ wired (130+48+520) |
| dropout=0.0 (shared map via lidar slot, ego blind) | **85 / 91** (drone-coll 0.7%) | ✅ shared-map code correct (≈ full_blind 88/90) |
| dropout=0.4 | 32 / 21, drop = **obstacle** collisions | ✅ sender-gating works |

> Note: dropout=0.4 here is a *worst case* (ego permanently blind + 40% senders blind). The B3 gate uses
> *partial* dropout (ego blind only part of the time), a much easier bar.

---

## B2 — Surgery + identity sanity
```powershell
& $py Phase_CD\Collab_Perception\surgical_expand_raster.py models\apex_ultra_glide_v14_comm8_lidar_final.zip models\raster_expanded_M0.zip
& $py Phase_CD\Collab_Perception\eval_raster.py models\raster_expanded_M0.zip 12 10 0.0 on 30
```
| check | expected | got |
|---|---|---|
| surgery self-check | `new 48 cols zero: True`, `expanded 1` | ✅ |
| expanded M0 @ lidar 12, no dropout | ≈ **92 / 95** (= M0; 48 shared weights are 0) | **92.0 / 95.0** ✅ |

> ✅ **CHECKPOINT B2 PASSED** — surgery identity-preserving, architecture wired correctly. Proceed to B3.

---

## B3 — THE GATE: train comm-ON vs comm-OFF under partial dropout (~5 M steps each)
```powershell
& $py Phase_CD\Collab_Perception\train_raster.py 5 10 0.4 on     # comm-ON  -> models\raster_l5_d0.4_ON_final.zip
& $py Phase_CD\Collab_Perception\train_raster.py 5 10 0.4 off    # comm-OFF -> models\raster_l5_d0.4_OFF_final.zip
& $py Phase_CD\Collab_Perception\eval_raster.py models\raster_l5_d0.4_ON_final.zip  5 10 0.4 on  200
& $py Phase_CD\Collab_Perception\eval_raster.py models\raster_l5_d0.4_OFF_final.zip 5 10 0.4 off 200
```
**RESULTS:**

| model (dropout 0.4) | d0.20 | d0.30 |
|---|---|---|
| comm-ON (`raster_l5_d0.4_ON`) |  |  |
| comm-OFF (`raster_l5_d0.4_OFF`) |  |  |
| **comm_value = ON − OFF (pp)** |  |  |

> ⛔ **CHECKPOINT B3 (make-or-break):** `comm_value ≥ ~5 pp` → shared channel is load-bearing → **B4**.
> `~0` → even partial dropout didn't induce channel use → tune dropout rate, or this is the limit.
> **Mechanism:** during a drone's blind windows, comm-OFF has *no* obstacle info (collisions ↑) while comm-ON
> has the shared map → that gap is the gradient pressure the flat no-dropout A2 lacked.
> **Tip:** watch the first ~1–2 M steps of the comm-ON run for early separation before letting both finish.
> **Tuning:** `dropout=0.4` is a start. comm-OFF too high (caution compensates) → raise dropout; both collapse
> (too harsh) → lower it. Bring early numbers to decide.

After the gate, also run feature-importance (adapt `feature_importance_collab.py` to 178/shared block) to
confirm the shared-map block is load-bearing (drop ≫ 0), mirroring the version-1 analysis.

---

## B4 — Attack + T-Cell trust  (DEFERRED — only if B3 passes)
False-hazard traitor poisons the shared map → no-defense drop → **trust-weighted fusion** (per-neighbor trust
from agreement with own lidar when active + cross-neighbor consensus + temporal consistency; down-weight liars
before rasterizing) → recovery, at f=1,2,3. Report vs **median / Krum** baselines + traitor-ID ROC + no-traitor
cost. Spec: `DESIGN_RASTER_TRUST.md`.

## Ledger
| stage | metric | d0.20 | d0.30 |
|---|---|---|---|
| B1 dropout=0 (validation) | success | 85 ✅ | 91 ✅ |
| B2 identity (lidar12,no-drop) | reproduce M0 | 92.0 ✅ | 95.0 ✅ |
| B3 gate | comm_value (pp) |  |  |

## When to bring to Claude
1. **After B2** — surgery identity (quick).
2. **After ~1–2 M of B3 comm-ON** — early separation check (avoid wasting full runs).
3. **After B3 gate** — the decisive comm_value; decides B4 vs tuning vs limit.
